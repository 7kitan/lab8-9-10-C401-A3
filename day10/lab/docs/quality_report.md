# Quality report — Lab Day 10 (nhóm)

**run_id:** good-run-v2 vs bad-run-v2  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu (V2 Dataset)

| Chỉ số | Tốt (good-run-v2) | Xấu (bad-run-v2) | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 31 | 31 | Dùng policy_export_dirty_v2.csv |
| cleaned_records | 15 | 15 | |
| quarantine_records | 16 | 16 | Bao gồm duplicate, empty text, và stale HR docs |
| Expectation halt? | No | Yes (stale_refund) | bad-run dùng --skip-validate |

---

## 2. Before / after retrieval (bắt buộc)

> Dẫn link tới: [good_eval_v2.csv](day10/lab/artifacts/eval/good_eval_v2.csv) và [bad_eval_v2.csv](day10/lab/artifacts/eval/bad_eval_v2.csv)

**Câu hỏi then chốt:** refund window (`q_refund_window`)  

**Trước (bad-run-v2):**  
- `top1_preview`: "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."
- `hits_forbidden`: **yes** (Lỗi: Top-k vẫn chứa chunk "Hoàn tiền voucher trong 14 ngày" từ bản raw chưa fix).

**Sau (good-run-v2):**  
- `top1_preview`: "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."
- `hits_forbidden`: **no** (Pipeline đã fix bản stale 14 ngày sang 7 ngày và đồng bộ hóa dữ liệu sạch).

**Merit (khuyến nghị):** versioning HR — `q_leave_version`  

**Trước/Sau:** Cả hai bản đều đạt `top1_doc_expected=yes`. Hệ thống tự động loại bỏ bản HR cũ (10 ngày từ 2025) vào `quarantine` dựa trên logic `effective_date < 2026-01-01`, đảm bảo Agent luôn đọc bản mới nhất là 12 ngày.

---

## 3. Freshness & monitor

- **Kết quả:** `PASS`
- **SLA:** 24 giờ.
- **Giải thích:** Dữ liệu trong `policy_export_dirty_v2.csv` có `latest_exported_at` là 2026-04-15T11:00:00. Tại thời điểm chạy (21:15), độ trễ chỉ khoảng ~10 giờ, nằm trong ngưỡng an toàn 24 giờ quy định.

---

## 4. Corruption inject (Sprint 3)

- **Cách làm hỏng:** Sử dụng flag `--no-refund-fix` kết hợp với file raw `policy_export_dirty_v2.csv` chứa nhiều dữ liệu rác và sai lệch (stale refund, html tags, wrong floor numbers).
- **Cách phát hiện:** 
    1. **Tầng Pipeline:** Expectation `refund_no_stale_14d_window` phát hiện ra các chuỗi "14 ngày" chưa được sửa và raise lỗi `HALT`.
    2. **Tầng Retrieval:** Script `eval_retrieval.py` quét top-k kết quả và phát hiện từ khóa cấm "14 ngày", đánh dấu `hits_forbidden=yes`. Dù Top-1 có thể đúng do độ tương đồng, nhưng ngữ cảnh (context) bị ô nhiễm dữ liệu sai.

---

## 5. Hạn chế & việc chưa làm

- Chưa tự động hóa việc so sánh biểu đồ phân phối dữ liệu (distribution) giữa các lần chạy.
- Cần mở rộng bộ câu hỏi golden lên ≥ 10 câu để đánh giá recall chính xác hơn.
