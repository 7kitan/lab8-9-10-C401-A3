# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Data Observability

**Họ và tên:** Nguyễn Văn Bách  
**Nhóm:** Group C401-A03  
**Vai trò:** Eval Owner  

---

## 1. Phần phụ trách cụ thể

Trong dự án Lab Day 10, tôi đảm nhận vai trò **Eval Owner**, trực tiếp phụ trách **Sprint 3: Inject Corruption & Before/After Evidence**. Nhiệm vụ chính của tôi bao gồm:
- Thiết kế kịch bản "làm hỏng" dữ liệu đầu vào để kiểm thử độ nhạy của hệ thống quan sát (Monitoring).
- Vận hành script `eval_retrieval.py` và `grading_run.py` để đo lường hiệu suất truy vấn trong hai trạng thái: dữ liệu rác (corrupted) và dữ liệu sạch (fixed).
- Phân tích kết quả và hoàn thiện tài liệu `docs/quality_report.md`, cung cấp bằng chứng định lượng về việc chất lượng dữ liệu ảnh hưởng trực tiếp đến câu trả lời của Agent.
- Phối hợp với team Ingestion và Embed để đảm bảo quy trình "Pruning" (xóa vector cũ) hoạt động chuẩn xác, tránh tình trạng "mồi cũ" hay dữ liệu stale làm sai lệch kết quả đánh giá cuối cùng.

## 2. Một quyết định kỹ thuật tiêu biểu

Một quyết định kỹ thuật quan trọng mà tôi thực hiện trong Sprint 3 là việc áp dụng và giải thích tham số `--skip-validate` trong `etl_pipeline.py`. 

Thông thường, một pipeline dữ liệu tốt phải dừng lại ngay (Halt) khi gặp vi phạm `Expectation` (ví dụ: phát hiện mẩu tin hoàn tiền 14 ngày thay vì 7 ngày). Tuy nhiên, để phục vụ mục tiêu quan sát (Observability), tôi đã quyết định cho phép pipeline "chạy cố" ngay cả khi fail validation. Việc này cho phép dữ liệu lỗi lọt vào Vector Store một cách có chủ đích. Kết quả là chúng ta có thể đo lường được tham số `hits_forbidden` ở tầng Retrieval. 

Quyết định này giúp team nhận ra rằng: **Chỉ có Dashboard xanh là chưa đủ**. Hệ thống có thể vẫn trả về kết quả nhìn có vẻ đúng ở Top-1 (Top-1 survivability), nhưng ngữ cảnh (Context) cung cấp cho LLM đã bị "ô nhiễm" bởi các mẩu tin cũ. Đây là bài học đắt giá về việc thiết kế Quality Gate nhiều lớp thay vì chỉ dựa vào tầng output cuối cùng.

## 3. Một sự cố hoặc Anomaly (Bất thường) đã giải quyết

Trong quá trình thực hiện Sprint 3, tôi phát hiện một hiện tượng bất thường: Sau khi chạy `eval_retrieval.py`, kết quả trong `bad_eval.csv` và `good_eval.csv` ở cột `top1_preview` hoàn toàn giống hệt nhau (đều trả về 7 ngày). Điều này làm cho bản báo cáo chất lượng trông có vẻ "vô thưởng vô phạt" vì không thấy được sự cải thiện.

**Phân tích nguyên nhân:** 
1. Do chúng tôi sử dụng file raw ban đầu (`policy_export_dirty.csv`) có quá ít bản ghi lỗi.
2. Model embedding `all-MiniLM-L6-v2` hoạt động khá tốt, nó vẫn xếp hạng mẩu tin 7 ngày (chuẩn) cao hơn mẩu tin 14 ngày (lỗi) dù cả hai đều tồn tại trong DB.
3. Tôi đã chạy pipeline mà quên trỏ tham số `--raw` tới phiên bản dữ liệu phức tạp hơn là `v2`.

**Giải pháp:** 
Tôi đã yêu cầu team Ingestion cung cấp file `policy_export_dirty_v2.csv` (31 bản ghi) và yêu cầu chạy lại toàn bộ quy trình với flag `--raw`. Kết quả mới cho thấy rõ ràng hơn: Dù Top-1 vẫn có thể trúng, nhưng cột `hits_forbidden` đã nhảy sang **Yes** ở bản Bad. Điều này minh chứng cho sự bất ổn của hệ thống khi không có cleaning rules. Tôi đã cập nhật lại toàn bộ `quality_report.md` dựa trên dữ liệu V2 này để đảm bảo tính thuyết phục.

## 4. Bằng chứng Before / After

Dưới đây là trích dẫn định lượng từ kết quả đánh giá sau khi đã fix quy trình dùng file V2:

| Metadata | Trạng thái Xấu (Corrupted) | Trạng thái Tốt (Fixed) |
|----------|---------------------------|------------------------|
| **Run ID** | `bad-run-v2` | `good-run-v2` |
| **Q: Refund Window** | `hits_forbidden: yes` | `hits_forbidden: no` |
| **Q: HR Leave** | `top1_doc_expected: yes` | `top1_doc_expected: yes` |
| **Freshness (SLA 24h)**| `PASS (~10h lag)` | `PASS (~10h lag)` |

Bản Bad chứa mẩu tin: *"Hoàn tiền voucher trong 14 ngày"* làm vấy bẩn kết quả tìm kiếm. Sau khi áp dụng rule fix trong `cleaning_rules.py`, mẩu tin này biến mất (hoặc được sửa), đưa `hits_forbidden` về `no`. Đây là bằng chứng quan trọng nhất để chứng minh giá trị của Sprint 3.

## 5. Cải tiến nếu có thêm 2 giờ làm việc

Nếu có thêm 2 giờ, tôi sẽ thực hiện hai cải tiến sau:
1. **Auto-Diff Eval:** Thay vì mở hai file CSV và so sánh bằng mắt, tôi sẽ viết một script Python nhỏ để tự động so sánh `bad_eval` và `good_eval`, sau đó xuất ra một bảng Markdown đẹp mắt chỉ chứa những dòng có thay đổi. Việc này sẽ giúp team quan sát nhanh hơn trong môi trường Production.
2. **Deep-Dive Embedding Distance:** Tôi muốn log lại khoảng cách vector (distance) của mẩu tin đúng vs mẩu tin sai. Điều này giúp giải thích tại sao đôi khi dữ liệu sai vẫn lọt vào Top-1 (hoặc tại sao nó bị đẩy xuống Top-2), từ đó tối ưu hóa được ngưỡng (threshold) cho Retriever.

---
**Cam kết:** Tôi đã trực tiếp thực hiện việc cấu hình eval, chạy các script nêu trên và tổng hợp báo cáo dựa trên số liệu thực tế từ artifacts hệ thống.
