# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Policy Refund v4 | CSV export (Policy DB) | Stale window (14d vs 7d), migration error markers | expectation[refund_no_stale_14d_window], strip_annotations |
| SLA P1 2026 | CSV export (SLA Tracker) | Duplicate contents | expectation[no_duplicate_chunk_text] |
| IT Helpdesk FAQ | CSV export (Confluence API) | Schema mismatch, date format DD/MM/YYYY | quarantine_records > 0, _normalize_effective_date |
| HR Leave Policy | CSV export (HR Portal) | Data lag / Stale version (bản 2025 vs 2026) | check_manifest_freshness / FAIL, quarantine stale_hr_policy |
| Access Control SOP | (Chưa trong export CSV — chỉ có file docs) | N/A — chưa ingest | Mở rộng: thêm vào allowlist khi cần |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID ổn định (hash: `{doc_id}_{seq}_{sha256[:16]}`) |
| doc_id | string | Có | Khóa logic (vd: policy_refund_v4) |
| chunk_text | string | Có | Nội dung chunk (min_length: 8, max_length: 2000) |
| effective_date | date | Có | Ngày hiệu lực (ISO YYYY-MM-DD) |
| exported_at | datetime | Có | Thời điểm export từ nguồn (required for lineage) |

---

## 3. Quy tắc quarantine vs drop

> Record lỗi đi vào file `quarantine_<id>.csv`. Data Owner định kỳ review và fix nguồn phát (DB/CSV) để replay.

- `unknown_doc_id`: ID không thuộc allowlist.
- `invalid_effective_date_format`: Không parse được ngày.
- `missing_effective_date`: Ngày hiệu lực rỗng.
- `stale_hr_policy_effective_date`: Bản HR cũ (< 2026).
- `missing_chunk_text`: Nội dung chunk rỗng.
- `duplicate_chunk_text`: Loại trùng nội dung (giữ bản đầu).
- `missing_exported_at`: Thiếu timestamp export (NEW — traceability requirement).

---

## 4. Quality rules (expectations)

| ID | Mô tả | Severity |
|----|--------|----------|
| min_one_row | Ít nhất 1 dòng sau clean | halt |
| no_empty_doc_id | Không doc_id rỗng | halt |
| refund_no_stale_14d_window | Không chunk refund chứa "14 ngày làm việc" | halt |
| chunk_min_length_8 | Chunk text ≥ 8 ký tự | warn |
| effective_date_iso_yyyy_mm_dd | Ngày hiệu lực đúng ISO | halt |
| hr_leave_no_stale_10d_annual | Không marker "10 ngày phép năm" trên HR | halt |
| no_empty_exported_at | Tất cả rows có exported_at (NEW) | warn |
| chunk_max_length_2000 | Chunk text ≤ 2000 ký tự (NEW) | halt |

---

## 5. Phiên bản & canonical

> `contracts/data_contract.yaml` định nghĩa `canonical_sources` và `policy_versioning`.

- Refund policy chuẩn: v4 (7 ngày làm việc).
- HR policy chuẩn: min effective date ≥ 2026-01-01.
- Owner team: CS & IT Helpdesk Team.
- Alert channel: #data-pipeline-alerts (Slack).
