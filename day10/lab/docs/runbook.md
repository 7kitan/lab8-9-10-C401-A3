# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

> User / agent thấy gì? (VD: trả lời "14 ngày" thay vì 7 ngày)

- **Agent / chatbot trả lời sai:** Khi user hỏi "bao nhiêu ngày hoàn tiền?", agent trả lời "14 ngày làm việc" thay vì "7 ngày làm việc" (bản policy v4 hiện hành).
- **HR policy outdated:** Agent nói "10 ngày phép năm" thay vì "12 ngày phép năm" (chính sách 2026).
- **Dấu hiệu gián tiếp:** User phản hồi "thông tin không đúng", ticket escalation tăng, hoặc CS agent phải override câu trả lời.

---

## Detection

> Metric nào báo? (freshness, expectation fail, eval `hits_forbidden`)

| Metric | Giá trị cảnh báo | File / lệnh kiểm tra |
|--------|-------------------|----------------------|
| `expectation[refund_no_stale_14d_window]` | FAIL (halt) | Log: `artifacts/logs/run_*.log` |
| `expectation[hr_leave_no_stale_10d_annual]` | FAIL (halt) | Log: `artifacts/logs/run_*.log` |
| `freshness_check` | FAIL (age > SLA 24h) | `python etl_pipeline.py freshness --manifest ...` |
| `ingest_publish_lag` | WARN (lag > 12h) | Log: ingest_publish_lag line |
| `hits_forbidden` (eval) | `yes` trên câu refund/HR | `artifacts/eval/before_after_eval.csv` |
| `contains_expected` (eval) | `no` (thiếu keyword) | `artifacts/eval/before_after_eval.csv` |

**Phát hiện thực tế trong lab:**
- Chạy `python etl_pipeline.py run --no-refund-fix --skip-validate` → Log hiện `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`.
- Eval inject: `q_refund_window` → `hits_forbidden=yes` (chunk stale "14 ngày" vẫn có trong top-k).

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` | Xác nhận `run_id`, `no_refund_fix`, `skipped_validate`. Nếu `no_refund_fix=true` → đã bỏ qua fix refund. |
| 2 | Mở `artifacts/quarantine/*.csv` | Xem dòng nào bị quarantine và lý do (`reason` column). Đếm `quarantine_records` khớp manifest. |
| 3 | Chạy `python eval_retrieval.py` | Xem `hits_forbidden` và `contains_expected` cho từng câu. Nếu `hits_forbidden=yes` → index có chunk stale. |
| 4 | Kiểm tra `artifacts/cleaned/*.csv` | Tìm chunk có "14 ngày làm việc" hoặc "10 ngày phép năm" — nếu tồn tại → cleaning rule chưa hoạt động. |
| 5 | Kiểm tra log freshness | `freshness_check=FAIL` → data cũ hơn SLA. `ingest_publish_lag=WARN` → pipeline chạy quá muộn sau khi data export. |

---

## Mitigation

> Rerun pipeline, rollback embed, tạm banner "data stale", …

1. **Rerun pipeline chuẩn:** `python etl_pipeline.py run --run-id fix-<timestamp>` (không dùng `--no-refund-fix`).
2. **Prune tự động:** Pipeline sẽ tự xoá vector ID cũ (stale 14-ngày chunk) qua prune step → `embed_prune_removed=1` trong log.
3. **Xác minh sau fix:** Chạy `python eval_retrieval.py --out artifacts/eval/after_fix.csv` → kiểm tra `hits_forbidden=no` cho tất cả câu.
4. **Tạm thời:** Nếu chưa fix được ngay, đặt banner "data đang cập nhật" trên chatbot/agent. Thông báo CS team biết để override manual.
5. **Freshness FAIL:** Cập nhật `exported_at` trong nguồn (chạy export mới) hoặc điều chỉnh `FRESHNESS_SLA_HOURS` nếu SLA thực tế cho phép data cũ hơn.

---

## Prevention

> Thêm expectation, alert, owner — nối sang Day 11 nếu có guardrail.

- **Expectation halt:** `refund_no_stale_14d_window` (halt) và `hr_leave_no_stale_10d_annual` (halt) đã có sẵn → pipeline tự dừng nếu stale data lọt qua.
- **Freshness SLA alert:** Cấu hình `FRESHNESS_SLA_HOURS=24` + alert channel `#data-pipeline-alerts` → notification khi FAIL.
- **2-boundary monitoring:** Đo cả freshness (data age) và ingest→publish lag → phát hiện pipeline chạy trễ.
- **Scheduled pipeline:** Đặt cron job chạy `etl_pipeline.py run` hàng ngày để đảm bảo index luôn fresh.
- **Data contract enforcement:** `contracts/data_contract.yaml` định nghĩa schema, owner, allowlist → đồng bộ khi thêm doc mới.
- **Day 11 guardrail:** Nếu có, thêm LLM-based check ("câu trả lời có nhất quán với policy version X không?") làm lớp phòng vệ cuối.
