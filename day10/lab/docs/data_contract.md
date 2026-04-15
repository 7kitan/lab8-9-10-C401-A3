# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Policy Refund v4 | CSV export (`policy_export_dirty_v2.csv`) | Stale window (14d vs 7d), migration error markers, voucher "14 ngày" | expectation[refund_no_stale_14d_window], rule fix 14→7 |
| SLA P1 2026 | CSV export (`policy_export_dirty_v2.csv`) | SLA resolution sai (2h thay vì 4h), mailbox size sai (100GB thay vì 50GB), duplicate | expectation[unique_chunk_id], rule fix SLA |
| IT Helpdesk FAQ | CSV export (`policy_export_dirty_v2.csv`) | HTML tags trong text, IT Room sai tầng (4 thay vì 3), date format DD/MM/YYYY và DD-MM-YYYY, lockout sai (3 thay vì 5) | expectation[no_html_tags], rule strip HTML, rule fix IT Room |
| HR Leave Policy | CSV export (`policy_export_dirty_v2.csv`) | Stale version 2025 (10 ngày), sai số phép (20 thay vì 15), offboarding delay (7 ngày thay vì ngay) | quarantine stale_hr_policy, rule fix HR 20→15, rule fix offboarding |
| Access Control SOP | CSV export (v2) — **chưa trong allowlist** | Quarantine tất cả vì `access_control_sop` chưa có trong `ALLOWED_DOC_IDS` | quarantine reason=unknown_doc_id |

> **Lưu ý:** `access_control_sop` có trong `canonical_sources` của `data_contract.yaml` nhưng **chưa** được thêm vào `ALLOWED_DOC_IDS` trong `cleaning_rules.py`. Tất cả chunk từ nguồn này bị quarantine.

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID ổn định (`{doc_id}_{seq}_{sha256[:16]}`) — hash từ `doc_id\|chunk_text\|seq` |
| doc_id | string | Có | Khóa logic — đã normalize lowercase (vd: `policy_refund_v4`) |
| chunk_text | string | Có | Nội dung chunk (min_length: 8), đã strip HTML tags |
| effective_date | date | Có | Ngày hiệu lực (ISO YYYY-MM-DD) — parse từ nhiều format |
| exported_at | datetime | Có | Thời điểm export từ nguồn |

---

## 3. Quy tắc quarantine vs drop

> Record lỗi đi vào file `quarantine_<id>.csv`. Data Owner định kỳ review và fix nguồn phát (DB/CSV) để replay.

- `unknown_doc_id`: ID không thuộc allowlist (vd: `legacy_catalog_xyz_zzz`, `unknown_system_xyz`, `access_control_sop`).
- `missing_effective_date`: Ngày hiệu lực rỗng (vd: row 5, row 16).
- `invalid_effective_date_format`: Không parse được ngày (vd: format `DD-MM-YYYY` ở row 15, `YYYY/MM/DD` ở row 29).
- `stale_hr_policy_effective_date`: Bản HR cũ (effective_date < 2026-01-01).
- `missing_chunk_text`: Nội dung chunk rỗng (vd: row 5, row 14).
- `duplicate_chunk_text`: Loại trùng nội dung (giữ bản đầu tiên, vd: row 2 trùng row 1).

---

## 4. Cleaning rules — Sprint 2 (business fixes)

> Baseline (6 rules) + Sprint 2 mở rộng (4 rules mới):

| Rule | Doc_id áp dụng | Exact match | Fix | Tag |
|------|---------------|-------------|-----|-----|
| Strip HTML tags | Tất cả | `<...>` regex | Xoá thẻ HTML | `[cleaned: html_tags]` |
| Fix HR leave 20→15 | `hr_leave_policy` | `"20 ngày phép"` | → `"15 ngày phép"` | `[cleaned: no_stale_hr_leave_20d]` |
| Fix HR offboarding | `hr_leave_policy` | `"trong 7 ngày"` | → `"ngay lập tức"` | `[cleaned: no_stale_hr_offboarding_7d]` |
| Fix IT Room floor | `it_helpdesk_faq` | `"IT Room tầng 4"` | → `"IT Room tầng 3"` | `[cleaned: no_stale_it_floor_4]` |
| Fix SLA mailbox | `sla_p1_2026` | `"hòm thư 100GB"` | → `"hòm thư 50GB"` | `[cleaned: no_stale_mailbox_100gb]` |
| Fix SLA P1 resolution | `sla_p1_2026` | `"resolution P1 là 2 giờ"` | → `"resolution P1 là 4 giờ"` | `[cleaned: no_stale_sla_p1_2h]` |

> Ghi chú: doc_id được normalize (`.strip().lower()`) trước khi check allowlist — cho phép match `ACCESS_CONTROL_SOP` → `access_control_sop`.

---

## 5. Quality rules (expectations)

| ID | Mô tả | Severity | Nguồn |
|----|--------|----------|-------|
| min_one_row | Ít nhất 1 dòng sau clean | halt | Baseline E1 |
| no_empty_doc_id | Không doc_id rỗng | halt | Baseline E2 |
| refund_no_stale_14d_window | Không chunk refund chứa "14 ngày làm việc" | halt | Baseline E3 |
| chunk_min_length_8 | Chunk text ≥ 8 ký tự | warn | Baseline E4 |
| effective_date_iso_yyyy_mm_dd | Ngày hiệu lực đúng ISO | halt | Baseline E5 |
| hr_leave_no_stale_10d_annual | Không marker "10 ngày phép năm" trên HR | halt | Baseline E6 |
| **no_html_tags** | Không chứa thẻ HTML trong chunk_text | **halt** | **Sprint 2 E7** |
| **unique_chunk_id** | Tất cả chunk_id phải duy nhất | **halt** | **Sprint 2 E8** |

---

## 6. Phiên bản & canonical

> `contracts/data_contract.yaml` định nghĩa `canonical_sources` và `policy_versioning`.

- **Owner team:** C401-A3
- **Alert channel:** c401-a3
- **Refund policy chuẩn:** v4 (7 ngày làm việc).
- **HR policy chuẩn:** min effective date ≥ 2026-01-01, 15 ngày phép (>5 năm KN), offboarding ngay lập tức.
- **SLA P1 chuẩn:** resolution 4 giờ.
- **IT chuẩn:** IT Room tầng 3, mailbox 50GB, lockout 5 lần.
- **Canonical sources:** `policy_export_dirty_v2.csv` (policy_refund_v4), `sla_p1_2026.txt`, `it_helpdesk_faq.txt`, `hr_leave_policy.txt`.
