# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** [Điền tên]  
**Vai trò:** Cleaning & Quality Owner / Embed & Monitoring  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ** (ngắn hơn Day 09 vì rubric slide cá nhân ~10% — vẫn phải đủ bằng chứng)

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `transform/cleaning_rules.py`: Thêm 3 rule mới (normalize_unicode, quarantine_empty_exported_at, strip_internal_annotations).
- `quality/expectations.py`: Thêm 2 expectation mới (no_empty_exported_at warn, chunk_max_length_2000 halt).
- `monitoring/freshness_check.py`: Thêm `check_ingest_publish_lag()` — đo lag 2 boundary (ingest → publish).
- `etl_pipeline.py`: Tích hợp lag check vào pipeline flow.
- `contracts/data_contract.yaml`: Điền owner_team, alert_channel, thêm quality rules mới.
- `docs/`: Viết pipeline_architecture.md, runbook.md, quality_report.md.

**Kết nối với thành viên khác:**

Tôi phụ trách phần cốt lõi: cleaning rules → expectations → monitoring. Output cleaned CSV được Embed Owner dùng để upsert vào Chroma. Kết quả freshness/lag được Docs Owner tham chiếu trong runbook.

**Bằng chứng (commit / comment trong code):**

Comment trong code: `# — RULE NEW:`, `# — EXPECTATION NEW:`, docstring `"""RULE NEW — ..."""`. Log: `artifacts/logs/run_clean-final.log`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

> VD: chọn halt vs warn, chiến lược idempotency, cách đo freshness, format quarantine.

Tôi chọn `chunk_max_length_2000` severity **halt** thay vì **warn** vì: chunk dài bất thường (>2000 ký tự) thường là dấu hiệu chunk bị concatenate do lỗi export (nhiều dòng CSV dính nhau, hoặc parser không nhận đúng delimiter). Nếu để warn, chunk corrupt này sẽ được embed → embedding vector không đại diện đúng nội dung → retrieval trả về kết quả sai. Halt đảm bảo pipeline dừng sớm để Data Owner kiểm tra nguồn.

Ngược lại, `no_empty_exported_at` chỉ ở mức **warn** vì: thiếu exported_at không ảnh hưởng trực tiếp đến chất lượng embedding hay retrieval — nó chỉ làm mất traceability cho freshness check. Pipeline vẫn có thể tiếp tục nhưng Data Owner cần được cảnh báo để fix nguồn.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

> Mô tả triệu chứng → metric/check nào phát hiện → fix.

**Triệu chứng:** Khi chạy inject (`--no-refund-fix --skip-validate`), eval cho `q_refund_window` báo `hits_forbidden=yes` — top-k chunk chứa "14 ngày làm việc" (stale policy v3).

**Phát hiện bởi:**
- Expectation log: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
- Eval CSV: `after_inject_bad.csv` dòng `q_refund_window` → `hits_forbidden=yes`

**Fix:** Rerun pipeline chuẩn (không flag inject): `python etl_pipeline.py run --run-id clean-final`. Pipeline tự:
1. Fix text "14 ngày" → "7 ngày" (cleaning rule baseline).
2. Strip annotation "(ghi chú: bản sync cũ...)" (rule mới strip_internal_annotations).
3. Prune vector stale từ Chroma (`embed_prune_removed=1`).
4. Upsert chunk clean → eval `hits_forbidden=no`. ✅

---

## 4. Bằng chứng trước / sau (80–120 từ)

> Dán ngắn 2 dòng từ `before_after_eval.csv` hoặc tương đương; ghi rõ `run_id`.

**run_id inject:** `inject-bad`
```
q_refund_window | contains_expected=yes | hits_forbidden=yes | top1_preview: "...14 ngày làm việc kể từ xác nhận đơn."
```

**run_id clean:** `clean-final`
```
q_refund_window | contains_expected=yes | hits_forbidden=no | top1_preview: "...7 ngày làm việc kể từ xác nhận đơn."
```

**Delta:** `hits_forbidden` chuyển từ `yes` → `no`. Expectation `refund_no_stale_14d_window` chuyển từ `FAIL` → `OK`. `embed_prune_removed=1` trong log clean-final (xoá chunk stale từ inject).

---

## 5. Cải tiến tiếp theo (40–80 từ)

> Nếu có thêm 2 giờ — một việc cụ thể (không chung chung).

Tôi sẽ refactor `hr_leave_min_effective_date` từ hard-code "2026-01-01" sang đọc từ `contracts/data_contract.yaml` (`policy_versioning.hr_leave_min_effective_date`). Chứng minh bằng inject: đổi cutoff thành "2025-06-01" → bản HR 2025-01-01 vẫn bị quarantine nhưng bản HR 2025-07-01 (nếu thêm) sẽ pass. Điều này đạt tiêu chí Distinction (d).
