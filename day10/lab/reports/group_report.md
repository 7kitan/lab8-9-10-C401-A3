# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| ___ | Ingestion / Raw Owner | ___ |
| ___ | Cleaning & Quality Owner | ___ |
| ___ | Embed & Idempotency Owner | ___ |
| ___ | Monitoring / Docs Owner | ___ |

**Ngày nộp:** ___________  
**Repo:** ___________  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

_________________

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

_________________

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| … | … | … | … |

**Rule chính (baseline + mở rộng):**

- …

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

_________________

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

_________________

**Kết quả định lượng (từ CSV / bảng):**

_________________

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

Nhóm chọn **SLA = 24 giờ** (cấu hình trong `.env`: `FRESHNESS_SLA_HOURS=24`), đo tại boundary **publish** (sau khi embed xong, manifest ghi `latest_exported_at`).

Khi chạy `run_id=sprint1`, freshness check trả về **FAIL**:

```
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 116.718, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Giải thích:** CSV mẫu có `exported_at = 2026-04-10T08:00:00` — đã cũ ~5 ngày so với thời điểm chạy (15/04). Trong production, FAIL này sẽ trigger alert theo `alert_channel` trong `data_contract.yaml` (`c401-a3-monitoring@gmail.com`). Đây là **hành vi mong đợi** trên data snapshot — nhóm ghi nhận trong `docs/runbook.md` mục Detection và giải thích rằng SLA áp cho "pipeline run" chứ không phải "data snapshot cố định".

| Trạng thái | Ý nghĩa | Hành động |
|------------|---------|----------|
| **PASS** | `age_hours ≤ 24` — dữ liệu tươi | Không cần hành động |
| **WARN** | Manifest thiếu timestamp | Kiểm tra pipeline có ghi `exported_at` không |
| **FAIL** | `age_hours > 24` — dữ liệu cũ quá SLA | Rerun pipeline hoặc cập nhật data source |

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

_________________

---

## 6. Rủi ro còn lại & việc chưa làm

- **Freshness chỉ đo 1 boundary (publish):** Chưa đo tại boundary ingest — nếu ingest xong nhưng embed fail, freshness vẫn báo FAIL nhưng không phân biệt được lỗi ở tầng nào. Cần thêm `ingest_timestamp` vào manifest (Distinction criteria).
- **Chưa có alert tự động:** `freshness_check.py` chỉ chạy manual hoặc cuối pipeline. Cần cron job hoặc webhook để gửi alert thực sự khi FAIL.
- **SLA cứng 24h chưa chắc phù hợp:** Policy PDF đổi 1 lần/tuần → SLA 168h có thể phù hợp hơn; ticket stream cần SLA ngắn hơn (4h). Nên phân biệt SLA theo loại nguồn.
- **Chưa có LLM-judge eval:** Hiện chỉ dùng keyword matching (`must_contain_any`, `must_not_contain`). Mở rộng với LLM-judge sẽ bắt được lỗi ngữ nghĩa tinh vi hơn.
- **Data v2 chưa test đầy đủ:** File `policy_export_dirty_v2.csv` (32 dòng) đã merge nhưng chưa chạy pipeline với `--raw` trỏ tới v2 để kiểm tra các rule mới.
