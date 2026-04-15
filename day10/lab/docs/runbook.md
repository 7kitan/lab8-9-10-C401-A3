# Runbook — Lab Day 10: Data Pipeline Incident Response

**Nhóm:** C401-A3  
**Owner:** Trần Trọng Giang (Monitoring / Docs Owner)  
**Cập nhật:** 2026-04-15  
**Pipeline:** `python etl_pipeline.py run`  
**Collection:** `day10_kb` (ChromaDB)

---

## Symptom

Agent / hệ thống RAG trả lời **sai nghiệp vụ** mặc dù pipeline vẫn báo `PIPELINE_OK`:

| Kịch bản | User thấy gì | Nguyên nhân gốc (data) |
|-----------|--------------|----------------------|
| **A — Stale refund window** | Agent trả lời "khách hàng có **14 ngày** làm việc để hoàn tiền" | Chunk `policy_refund_v4` chứa bản sync cũ v3 (`14 ngày làm việc`); version đúng (v4) là **7 ngày** |
| **B — HR version conflict** | Agent trả lời "nhân viên dưới 3 năm được **10 ngày** phép năm" | Chunk `hr_leave_policy` bản HR 2025 (`effective_date < 2026-01-01`) chưa bị quarantine; version 2026 là **12 ngày** |
| **C — Freshness SLA vượt ngưỡng** | Không có triệu chứng rõ trên UI, nhưng dữ liệu đã quá cũ so với SLA | `exported_at` trong manifest cũ hơn `FRESHNESS_SLA_HOURS` (24h) |

**Câu hỏi golden phát hiện nhanh nhất:**
- `q_refund_window`: "Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền?"
- `q_leave_version`: "Nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?"

---

## Detection

**3 metric/check chính để phát hiện incident:**

| # | Metric / Check | Lệnh / File | Ngưỡng cảnh báo |
|---|---------------|-------------|-----------------|
| 1 | **Freshness SLA** | `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run_id>.json` | `FAIL` nếu `age_hours > 24` |
| 2 | **Expectation suite** | Log trong `artifacts/logs/run_<run_id>.log` | Bất kỳ `expectation[...] FAIL (halt)` |
| 3 | **Eval retrieval** | `python eval_retrieval.py --out artifacts/eval/before_after_eval.csv` | `hits_forbidden=yes` hoặc `contains_expected=no` |

**Ví dụ log phát hiện (từ run_id=sprint1):**

```
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 116.718, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Thứ tự ưu tiên kiểm tra (từ slide Day 10):**
```
Freshness / version → Volume & errors → Schema & contract → Lineage / run_id → mới đến model/prompt
```

---

## Diagnosis

| Bước | Việc làm | Lệnh / File | Kết quả mong đợi |
|------|----------|-------------|------------------|
| 1 | Kiểm tra **freshness** manifest gần nhất | `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint1.json` | Xem `age_hours` vs `sla_hours=24`. Nếu FAIL → data đã cũ, cần re-ingest |
| 2 | Kiểm tra **volume** pipeline | Đọc log: `raw_records`, `cleaned_records`, `quarantine_records` | `run_sprint1.log`: raw=10, cleaned=6, quarantine=4. Tỷ lệ quarantine 40% — cần xem có bất thường không |
| 3 | Mở **quarantine CSV** | `artifacts/quarantine/quarantine_sprint1.csv` | Kiểm tra cột `reason`: `unknown_doc_id`, `missing_effective_date`, `stale_hr_policy`, `duplicate_chunk_text` |
| 4 | Kiểm tra **expectation log** | Tìm dòng `expectation[...] FAIL` trong log | Nếu `refund_no_stale_14d_window FAIL` → chunk refund chưa được fix. Nếu `hr_leave_no_stale_10d_annual FAIL` → chunk HR cũ lọt vào cleaned |
| 5 | Chạy **eval retrieval** so sánh | `python eval_retrieval.py --out artifacts/eval/diagnosis_check.csv` | Kiểm tra `hits_forbidden` cho `q_refund_window` và `contains_expected` cho `q_leave_version` |

**Timebox diagnosis:** tối đa **20 phút**. Nếu chưa tìm ra root cause → chuyển sang Mitigation (rollback trước).

---

## Mitigation

**Hành động khẩn cấp (timebox ~15 phút):**

| Ưu tiên | Hành động | Lệnh | Ghi chú |
|---------|----------|------|---------|
| 1 | **Rerun pipeline chuẩn** (fix refund + validate) | `python etl_pipeline.py run --run-id hotfix-<timestamp>` | Không dùng `--no-refund-fix` hoặc `--skip-validate` |
| 2 | **Verify bằng eval** | `python eval_retrieval.py --out artifacts/eval/after_hotfix.csv` | Kiểm tra `hits_forbidden=no` và `contains_expected=yes` |
| 3 | **Thông báo team** nếu P1 | Ghi nhận vào `artifacts/logs/` + thông báo qua `alert_channel` | Nếu agent đang serve production → tạm treo hoặc banner "Dữ liệu đang cập nhật" |

**Nếu data source chưa fix (CSV gốc vẫn sai):**
- Cô lập dữ liệu sai bằng cách thêm vào quarantine thủ công
- Chạy pipeline với `--run-id rollback-<date>` trên bản cleaned data cuối cùng đã verified
- Ghi nhận trong log: lý do rollback, run_id trước/sau

**Kiểm tra idempotency sau hotfix:**
- Chạy pipeline 2 lần liên tiếp → `embed_upsert count` phải bằng nhau
- Collection count trong Chroma không tăng thêm

---

## Prevention

**Biện pháp phòng ngừa sau sự cố:**

| # | Hành động | Owner | Deadline |
|---|----------|-------|----------|
| 1 | **Thêm expectation** kiểm tra `exported_at` không quá cũ so với SLA (vd: `max_age_exported_at_hours`) | Quality Owner | Sprint tiếp theo |
| 2 | **Thiết lập alert tự động** khi `freshness_check=FAIL` → gửi email `c401-a3-monitoring@gmail.com` (config trong `data_contract.yaml`) | Monitoring Owner (Giang) | Đã cấu hình trong contract |
| 3 | **Review runbook** sau mỗi incident: cập nhật bảng Diagnosis nếu phát hiện pattern mới | Monitoring Owner | Sau mỗi incident |
| 4 | **Đồng bộ contract**: khi thêm doc_id mới vào allowlist → cập nhật `data_contract.yaml` + `cleaning_rules.py` đồng thời | Cleaning Owner + Monitoring Owner | Mỗi lần đổi schema |
| 5 | **Nối Day 11 guardrail**: nếu có safety layer, thêm check data freshness trước khi agent respond cho user | Team | Day 11 |

**Expectation mới đề xuất sau incident:**
```python
# E_new: exported_at không quá cũ (> 48h cảnh báo)
stale_export = [r for r in cleaned_rows 
                if r.get("exported_at") and age_hours(r["exported_at"]) > 48]
# severity: "warn" (không halt — để pipeline tiếp tục nhưng ghi nhận)
```
