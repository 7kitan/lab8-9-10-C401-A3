# Quality report — Lab Day 10 (nhóm)

**run_id:** `clean-final` (pipeline chuẩn) / `inject-bad` (Sprint 3 inject)  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (inject-bad) | Sau (clean-final) | Ghi chú |
|--------|---------------------|--------------------|---------|
| raw_records | 10 | 10 | Cùng file CSV raw |
| cleaned_records | 6 | 6 | Số lượng bằng nhau nhưng nội dung khác |
| quarantine_records | 4 | 4 | Rows: 2 (dup), 5 (missing date), 7 (HR stale), 9 (unknown doc_id) |
| Expectation halt? | **Có** — `refund_no_stale_14d_window FAIL` (bypass `--skip-validate`) | **Không** — tất cả 8 expectations OK | Fix refund 14→7 giải quyết violation |

---

## 2. Before / after retrieval (bắt buộc)

> Đính kèm hoặc dẫn link tới `artifacts/eval/before_after_eval.csv` (hoặc 2 file before/after).

**Câu hỏi then chốt:** refund window (`q_refund_window`)

**Trước (inject — `--no-refund-fix`):**
```
q_refund_window | top1: policy_refund_v4 | preview: "...14 ngày làm việc kể từ xác nhận đơn." | contains_expected=yes | hits_forbidden=yes
```
→ Chunk stale "14 ngày" có mặt trong top-k → agent sẽ trả lời sai.

**Sau (clean — pipeline chuẩn):**
```
q_refund_window | top1: policy_refund_v4 | preview: "...7 ngày làm việc kể từ xác nhận đơn." | contains_expected=yes | hits_forbidden=no
```
→ Chunk đã fix "7 ngày", không còn forbidden content.

**Merit (khuyến nghị):** versioning HR — `q_leave_version` (`contains_expected`, `hits_forbidden`, cột `top1_doc_expected`)

**Trước (inject):**
```
q_leave_version | top1: hr_leave_policy | contains_expected=yes | hits_forbidden=no | top1_doc_expected=yes
```

**Sau (clean):**
```
q_leave_version | top1: hr_leave_policy | contains_expected=yes | hits_forbidden=no | top1_doc_expected=yes
```
→ Cả inject lẫn clean đều đạt cho `q_leave_version` vì baseline đã quarantine bản HR cũ (2025, "10 ngày phép năm") dựa trên `effective_date < 2026-01-01`. Chỉ bản HR 2026 ("12 ngày phép năm") tồn tại trong cleaned.

**File eval:** `artifacts/eval/after_clean_eval.csv` (clean) và `artifacts/eval/after_inject_bad.csv` (inject).

---

## 3. Freshness & monitor

> Kết quả `freshness_check` (PASS/WARN/FAIL) và giải thích SLA bạn chọn.

- **SLA:** `FRESHNESS_SLA_HOURS=24` (mặc định — data không nên cũ hơn 24 giờ kể từ thời điểm export).
- **Kết quả trên data mẫu:** `freshness_check=FAIL` — `latest_exported_at=2026-04-10T08:00:00`, `age_hours≈120h` → vượt SLA 24h.
- **Ingest→Publish lag:** `WARN` — `ingest_publish_lag_hours≈120h`, `lag_warn_hours=12.0` → pipeline chạy rất muộn so với thời điểm data export.
- **Giải thích:** FAIL là hợp lý — CSV mẫu có `exported_at` cố định từ ngày 10/04. Trong production, nguồn sẽ export mới hàng ngày và pipeline chạy tự động → freshness PASS.

---

## 4. Corruption inject (Sprint 3)

> Mô tả cố ý làm hỏng dữ liệu kiểu gì (duplicate / stale / sai format) và cách phát hiện.

**Kịch bản inject:**
```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
```

- **Loại inject:** Bỏ qua fix refund window (14→7 ngày) bằng flag `--no-refund-fix`.
- **Hậu quả:**
  - Expectation `refund_no_stale_14d_window` **FAIL** (halt) → pipeline ghi log FAIL nhưng tiếp tục embed nhờ `--skip-validate`.
  - Chunk stale "14 ngày làm việc" được embed vào Chroma → eval cho `q_refund_window` hiện `hits_forbidden=yes`.
  - Prune cũng xoá chunk cũ (từ run clean trước) để thay bằng chunk inject → `embed_prune_removed=1`.

**Cách phát hiện:**
1. Log: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
2. Eval: `q_refund_window` → `hits_forbidden=yes`
3. Manifest: `"no_refund_fix": true`, `"skipped_validate": true`

---

## 5. Hạn chế & việc chưa làm

- Chưa tích hợp Great Expectations (GE) hoặc pydantic model — dùng custom expectations đơn giản.
- HR policy cutoff hard-code `2026-01-01` — nên đọc từ config/env.
- Chưa có multi-source ingestion (chỉ 1 file CSV).
- Chưa có LLM-judge eval — chỉ dùng keyword-based retrieval check.
- Freshness alert chưa tích hợp Slack/email thực tế — chỉ ghi log.
