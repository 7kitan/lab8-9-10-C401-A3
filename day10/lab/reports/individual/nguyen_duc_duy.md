# Báo cáo cá nhân — Lab Day 10

**Họ và tên:** Nguyễn Đức Duy
**Vai trò:** Monitoring / Docs Owner  
**Độ dài:** ~450 từ

---

## 1. Phụ trách

Tôi phụ trách viết tài liệu kiến trúc và data contract cho pipeline:

- `docs/pipeline_architecture.md`: Vẽ sơ đồ Mermaid toàn bộ luồng ETL (10 bước clean → 8 expectations → embed → monitor), bảng ranh giới trách nhiệm 5 thành phần, mô tả idempotency, liên hệ Day 09, và ghi nhận rủi ro.
- `docs/data_contract.md`: Mô tả 5 nguồn dữ liệu (source map), schema cleaned 5 cột, 6 lý do quarantine, bảng 6 Sprint 2 cleaning rules (exact match + tag), bảng 8 expectations (7 halt + 1 warn), và canonical versions.

**Kết nối với thành viên khác:** Tôi đọc code `cleaning_rules.py` và `expectations.py` của Cleaning Owner để trích xuất chính xác tên rule, severity, exact match pattern. Output docs giúp nhóm đồng bộ hiểu ranh giới pipeline và Data Contract YAML.

**Bằng chứng:** commit trên nhánh `main`, file `docs/pipeline_architecture.md` và `docs/data_contract.md` trong repo.

---

## 2. Quyết định kỹ thuật

**Cấu trúc data contract theo failure mode:** Tôi chọn tổ chức bảng source map theo **failure mode chính** (cột thứ 3) thay vì chỉ liệt kê nguồn. Ví dụ: nguồn `Policy Refund v4` có failure mode "Stale window (14d vs 7d), voucher 14 ngày" → mapping trực tiếp sang metric `expectation[refund_no_stale_14d_window]`. Cách này giúp khi có incident, người đọc runbook tra ngược từ metric → failure mode → nguồn → fix.

**Ghi nhận `access_control_sop` chưa trong allowlist:** `data_contract.yaml` liệt kê `access_control_sop` trong `canonical_sources`, nhưng `ALLOWED_DOC_IDS` trong `cleaning_rules.py` chỉ có 4 IDs. Tôi ghi rõ trong data_contract.md rằng tất cả chunk từ nguồn này bị quarantine `unknown_doc_id` — đây là gap cần đồng bộ giữa contract và code.

---

## 3. Sự cố / anomaly

Khi viết pipeline_architecture.md, tôi phát hiện Sprint 2 cleaning rules (strip HTML, fix HR, fix IT Room, fix SLA) đều dùng **exact string match** — ví dụ `"IT Room tầng 4"`. Nếu nguồn CSV thay đổi wording (viết "IT room tầng 4" lowercase), rule sẽ không bắt được.

Tôi ghi vào mục "Rủi ro đã biết" (section 5) để Cleaning Owner review. Đồng thời cross-check `data_contract.yaml` thấy `doc_id` đã được normalize lowercase (`doc_id = (doc_id or "").strip().lower()` tại L93), nhưng `chunk_text` thì không — xác nhận rủi ro này là thật.

---

## 4. Before/after

Dựa trên log `artifacts/logs/run_sprint1.log` (trước Sprint 2 — chỉ 6 expectations baseline):
```
expectation[min_one_row] OK (halt) :: cleaned_rows=6
...
freshness_check=FAIL {"age_hours": 116.718, "sla_hours": 24.0}
```

Sau khi nhóm thêm Sprint 2 expectations, log `run_clean-final.log` hiện thêm:
```
expectation[no_html_tags] OK (halt)
expectation[unique_chunk_id] OK (halt)
```

Docs trước: template rỗng (chỉ có `…`, `___`). Sau: pipeline_architecture.md có Mermaid diagram đầy đủ, data_contract.md có 6 bảng chi tiết với data thật.

---

## 5. Cải tiến thêm 2 giờ

Tôi sẽ viết script `validate_contract_sync.py` so sánh `ALLOWED_DOC_IDS` trong `cleaning_rules.py` với `canonical_sources` trong `data_contract.yaml` — báo lỗi nếu có doc_id trong contract mà chưa trong allowlist (như `access_control_sop` hiện tại). Chạy script này trong CI để đảm bảo code và contract luôn đồng bộ.
