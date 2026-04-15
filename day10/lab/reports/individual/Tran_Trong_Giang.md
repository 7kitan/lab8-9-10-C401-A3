# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trần Trọng Giang  
**Vai trò:** Monitoring / Docs Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `docs/runbook.md` — viết toàn bộ runbook incident response (5 mục: Symptom → Detection → Diagnosis → Mitigation → Prevention)
- `monitoring/freshness_check.py` — sử dụng và kiểm tra logic freshness SLA trên manifest pipeline
- `reports/group_report.md` — viết mục 4 (Freshness & monitoring) và mục 6 (Rủi ro còn lại)
- `contracts/data_contract.yaml` — cấu hình `alert_channel` và review `freshness.measured_at`

**Kết nối với thành viên khác:**

Tôi nhận output từ Cleaning/Quality Owner (Sprint 2) — đặc biệt là log `run_sprint1.log` chứa kết quả 8 expectation (6 baseline + 2 mới: `no_html_tags`, `unique_chunk_id`) và số liệu `raw=10, cleaned=6, quarantine=4`. Dựa trên log này, tôi xây dựng runbook với metric cụ thể và mô tả diagnosis path.

**Bằng chứng (commit / comment trong code):**

Commit cập nhật `docs/runbook.md` từ template 36 dòng thành runbook hoàn chỉnh ~100 dòng với bảng Diagnosis 5 bước, bảng Mitigation 3 hành động, và bảng Prevention 5 biện pháp.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Quyết định: Chọn boundary đo freshness tại "publish" thay vì "ingest"**

Khi viết runbook và cấu hình `data_contract.yaml`, tôi phải chọn `measured_at: "publish"` hay `"ingest"`. Tôi chọn **publish** vì lý do sau:

- Nếu đo tại ingest, pipeline có thể báo PASS (data đã nhập) nhưng embed chưa xong → Agent vẫn đọc data cũ từ Chroma. Đây là trường hợp "pipeline green nhưng user vẫn thấy cũ" mà slide 8 đã cảnh báo.
- Đo tại publish (sau embed xong, manifest ghi `latest_exported_at`) đảm bảo metric phản ánh đúng thời điểm data **thực sự visible** cho Agent.

**Trade-off:** Đo tại publish không phân biệt được lỗi ở ingest hay embed khi FAIL. Tôi ghi nhận đây là rủi ro trong mục 6 group report và đề xuất thêm `ingest_timestamp` vào manifest cho Distinction.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Anomaly: Freshness check FAIL trên data mẫu — "false alarm" hay hành vi đúng?**

Khi chạy `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint1.json`, kết quả:

```
FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 116.718, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Ban đầu tôi nghĩ đây là lỗi pipeline. Sau khi kiểm tra, `exported_at` trong CSV là `2026-04-10T08:00:00` — cách ngày chạy (15/04) khoảng 5 ngày → tất nhiên vượt SLA 24h.

**Fix:** Đây không phải lỗi — đây là **hành vi mong đợi** trên data snapshot cố định. Tôi ghi rõ trong runbook: SLA áp cho "pipeline run production" (data source cập nhật liên tục) chứ không phải "data snapshot giáo dục". Nhóm có thể đổi `FRESHNESS_SLA_HOURS=168` (7 ngày) trong `.env` để PASS trên data mẫu, nhưng quan trọng là phải **giải thích nhất quán** — tôi chọn giữ 24h và giải thích trong runbook + group report.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**run_id:** `sprint1`

Từ `artifacts/logs/run_sprint1.log`:

| Metric | Giá trị | Ý nghĩa |
|--------|---------|---------|
| `raw_records` | 10 | Tổng dòng CSV đầu vào |
| `cleaned_records` | 6 | Sau khi áp 6 baseline rules |
| `quarantine_records` | 4 | Bị loại (unknown_doc_id, duplicate, stale HR, missing date) |
| `freshness_check` | FAIL | `age_hours=116.7 > sla_hours=24` |
| Expectations (8 checks) | All OK | 6 baseline + 2 mới (no_html_tags, unique_chunk_id) |

Sau khi viết runbook, nếu incident xảy ra (VD: inject `--no-refund-fix --skip-validate`), team có thể follow đúng 5 bước Diagnosis để tìm root cause (expectation `refund_no_stale_14d_window FAIL`) và 3 bước Mitigation (rerun pipeline chuẩn → verify eval → thông báo team).

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ **thêm freshness đo ở 2 boundary** (ingest + publish): ghi `ingest_timestamp` vào manifest ngay sau `load_raw_csv()` và so sánh với `run_timestamp` (publish). Khi freshness FAIL, dựa vào khoảng cách giữa 2 timestamp để phân biệt: lỗi ở data source (ingest cũ) hay lỗi ở pipeline transform/embed (khoảng cách ingest→publish bất thường). Đây là tiêu chí **Distinction** theo `SCORING.md`.
