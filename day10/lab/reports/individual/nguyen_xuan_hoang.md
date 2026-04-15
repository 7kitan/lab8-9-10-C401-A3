# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Xuân Hoàng  
**Vai trò:** Cleaning & Quality Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài:** ~550 từ

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

Trong dự án Day 10, tôi đảm nhận vai trò **Cleaning & Quality Owner**, chịu trách nhiệm thiết lập các quy tắc làm sạch dữ liệu và xây dựng "hàng rào kỹ thuật" (quality gates) để đảm bảo tính tin cậy của Vector Store.

**File / module:**
- `transform/cleaning_rules.py`: Tôi trực tiếp xây dựng các rule xử lý business logic (như fix số ngày phép HR, đổi tầng phòng IT) và rule kỹ thuật (loại bỏ thẻ HTML).
- `quality/expectations.py`: Tôi thiết lập bộ quy tắc kiểm định (Expectation Suite) với cơ chế `halt` để ngăn chặn dữ liệu rác được publish vào ChromaDB.

Tôi phối hợp với bạn Nguyễn Tuấn Kiệt (Ingestion Owner) để đảm bảo dữ liệu raw được parse đúng trước khi clean, và phối hợp với bạn Nguyễn Văn Bách (Eval Owner) để kiểm chứng xem các rule clean của tôi có thực sự giúp giảm tỉ lệ `hits_forbidden` hay không.

**Bằng chứng:** Các rule xử lý từ dòng 138-166 trong `cleaning_rules.py` và các expectation E7, E8 trong `expectations.py`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Một quyết định quan trọng mà tôi đưa ra là áp dụng cơ chế **Halt (Stop Pipeline)** cho expectation `no_html_tags`. Thay vì chỉ cảnh báo (`warn`), tôi quyết định dừng toàn bộ luồng publish nếu phát hiện bất kỳ thẻ HTML nào (`<.../>`) còn sót lại trong chunk_text.

**Lý do:** Các thẻ HTML không chỉ là nhiễu (noise) làm tăng kích thước index mà còn đánh lừa mô hình Embedding (như `text-embedding-3-small`), vốn tập trung vào ngữ nghĩa tự nhiên. Việc để lọt mã HTML vào Vector Store sẽ làm nhiễu không gian vector, dẫn đến việc Agent có thể truy vấn sai các đoạn text kỹ thuật thay vì nội dung chính sách. Bằng việc đặt severity là `halt`, tôi buộc hệ thống phải "sạch tuyệt đối" ở boundary này, đảm bảo tính ổn định cho các thành viên phụ trách Retrieval phía sau.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Trong quá trình chạy Sprint 2, tôi phát hiện một anomaly nghiêm trọng về tính nhất quán phiên bản (Version Alignment) trong tài liệu `hr_leave_policy`. Cụ thể, dữ liệu raw chứa thông báo về "20 ngày phép năm", trong khi chính sách mới nhất của công ty năm 2026 yêu cầu đồng bộ về "15 ngày phép".

Tôi đã thiết lập rule `no_stale_hr_leave_20d` để tự động replace nội dung này và đính kèm marker `[cleaned: no_stale_hr_leave_20d]` vào text. Để kiểm soát lỗi này không tái diễn khi có nguồn dữ liệu mới, tôi thêm expectation `hr_leave_no_stale_10d_annual` (và mở rộng cho 20d) với mức độ `halt`. 

**Kết quả:** Log hệ thống tại `run_sprint2_final.log` xác nhận:
`expectation[hr_leave_no_stale_10d_annual] OK (halt) :: violations=0`
Việc xử lý này giúp Agent không trả lời sai về quyền lợi nhân viên, một lỗi nhạy cảm có thể gây rủi ro vận hành cao.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Dưới đây là bằng chứng về hiệu quả của việc kiểm soát chất lượng dữ liệu (trích xuất từ `run_sprint2_final.log` với `run_id=sprint2_final`):

```log
expectation[no_html_tags] OK (halt) :: violations=0
expectation[unique_chunk_id] OK (halt) :: total=15
PIPELINE_OK
```

Về mặt retrieval, nhờ rule fix HR stale, kết quả eval tại `before_after_eval.csv` cho thấy:
- **Câu hỏi `q_leave_version`**: `Good Run (hits_forbidden) = no`.
Dữ liệu sai lệch đã bị chặn đứng hoặc sửa đổi ngay tại tầng Ingestion, đảm bảo Agent luôn truy cập được "Single Source of Truth".

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ triển khai **PII Detection** (phát hiện thông tin cá nhân) bằng Regex hoặc thư viện `presidio`. Hiện tại pipeline mới chỉ làm sạch noise kỹ thuật, nhưng chưa bảo vệ được các thông tin nhạy cảm như email cá nhân hoặc số điện thoại có thể lọt vào file export. Việc tự động "masking" các thông tin này trước khi embed sẽ giúp hệ thống tuân thủ bảo mật dữ liệu tốt hơn.
