# Quality report — Lab Day 10 (nhóm)

**run_id:** good-run vs bad-run  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Tốt (good-run) | Xấu (bad-run) | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 10 | 10 | |
| cleaned_records | 6 | 6 | |
| quarantine_records | 4 | 4 | |
| Expectation halt? | No | Yes (stale_refund) | bad-run dùng --skip-validate |

---

## 2. Before / after retrieval (bắt buộc)

> Dẫn link tới: [good_eval.csv](day10/lab/artifacts/eval/good_eval.csv) và [bad_eval.csv](day10/lab/artifacts/eval/bad_eval.csv)

**Câu hỏi then chốt:** refund window (`q_refund_window`)  

**Trước (bad-run):**  
- `top1_preview`: "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."
- `hits_forbidden`: **yes** (Do vector store vẫn chứa chunk stale 14 ngày vì không áp dụng fix).

**Sau (good-run):**  
- `top1_preview`: "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."
- `hits_forbidden`: **no** (Pipeline đã fix bản stale 14 ngày và đồng bộ hóa dữ liệu sạch).

**Merit (khuyến nghị):** versioning HR — `q_leave_version`  

**Trước/Sau:** Cả hai bản đều đạt `top1_doc_expected=yes` vì rule quarantine bản HR cũ đã được cài đặt cứng trong baseline và không bị ảnh hưởng bởi flag `--no-refund-fix`.

---

## 3. Freshness & monitor

- **Kết quả:** `FAIL`
- **SLA:** 24 giờ.
- **Giải thích:** Dữ liệu mẫu `policy_export_dirty.csv` có `exported_at` là 2026-04-10, tính đến thời điểm chạy lab (2026-04-15) đã quá 24h quy định. Trong thực tế, điều này sẽ kích hoạt cảnh báo tới đội Data Engineering để kiểm tra xem Job Export có bị treo hay không.

---

## 4. Corruption inject (Sprint 3)

- **Cách làm hỏng:** Sử dụng flag `--no-refund-fix` để vô hiệu hóa logic sửa lỗi `14 ngày -> 7 ngày` trong `cleaning_rules.py`.
- **Cách phát hiện:** 
    1. **Tầng Pipeline:** Expectation `refund_no_stale_14d_window` phát hiện ra chuỗi "14 ngày làm việc" và raise lỗi `HALT`.
    2. **Tầng Retrieval:** Script `eval_retrieval.py` quét top-k và phát hiện thấy từ khóa cấm "14 ngày", đánh dấu `hits_forbidden=yes`.

---

## 5. Hạn chế & việc chưa làm

- Chưa tích hợp report tự động gửi qua email/Slack khi pipeline FAIL.
- Phối hợp với team Infrastructure để tự động trigger pipeline khi có file mới trong thư mục `data/raw`.
