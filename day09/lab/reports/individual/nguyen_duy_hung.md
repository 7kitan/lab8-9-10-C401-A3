# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Duy Hưng  
**Vai trò trong nhóm:** Trace & Docs Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- Các file Python: `eval_trace.py`
- Các file Docs: `docs/routing_decisions.md`, `docs/single_vs_multi_comparison.md`, và `reports/group_report.md`.
- Công việc chính: Implement các hàm đo lường `analyze_trace()`, `compare_single_vs_multi()`, và chạy lệnh `python eval_trace.py --grade` để xuất ra kết quả chấm điểm cuối cùng.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Công việc của tôi chủ yếu diễn ra ở Phase 6 - giai đoạn chốt sổ. Tôi đóng vai trò Đảm bảo Chất lượng (QA). Tôi phải đợi Duy, Giang, và Bách hoàn thiện xong luồng `graph.py` và các `workers`, sau đó mới có thể chạy file test `grading_questions.json`. Kết quả `artifacts/grading_run.jsonl` từ máy tôi là bằng chứng "sống" duy nhất chứng minh đồ thị Multi-Agent của nhóm thực sự hoạt động chuẩn xác, và là đầu vào bắt buộc cho các báo cáo kỹ thuật.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
Các thay đổi trực tiếp trong file `eval_trace.py` bổ sung tham số tiếng Việt và phần viết hoàn chỉnh cho toàn bộ thư mục `docs/`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tích hợp trực tiếp (Hard-code) các metric gốc (Baseline) của Day 08 vào lệnh xuất báo cáo so sánh trong `eval_trace.py` thay vì phụ thuộc vào một file lưu trữ lịch sử ngoài.

**Lý do:**
Hệ thống template yêu cầu soạn ra mảng so sánh giữa Single-Agent và Multi-Agent. Tuy nhiên, việc tái thiết lập môi trường cũ hoặc truy suất qua API để tìm file log của Day 08 tốn rất nhiều thời gian và gây rủi ro cao (Crash/FileNotFound) khi chạy test cục bộ dưới sức ép thời gian sát nộp bài.

**Trade-off đã chấp nhận:**
Chấp nhận mất đi tính linh động tự động 100%. Nếu các tham số test của lab Day 08 thay đổi, tôi phải mở code nguồn ra để thay đổi thủ công. Đổi lại, file `eval_trace.py` trở nên tự trị (standalone), đảm bảo 100% luôn chạy thành công xuất được file so sánh vào phút 89.

**Bằng chứng từ trace/code:**
```python
# eval_trace.py - Đưa thông số Day 08 vào cứng để đối soát nhanh gọn
        day08_baseline = {
            "accuracy": Day08_Accuracy_Param,
            "latency_ms": 1800,
            "abstain_rate": Day08_Abstain_Param
        }
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Bị sập script khi đọc và in ra Trace Log do lỗi giải mã Encoding: `UnicodeDecodeError`.

**Symptom (pipeline làm gì sai?):**
Khi chạy lệnh `--grade`, Pipeline hoàn thành việc chạy câu hỏi thông qua AI nhưng khi thư viện Python quét để gộp log lưu vào file `.jsonl` hoặc tính metric tổng, Terminal Windows lập tức văng lỗi và dừng hẳn tiến trình, bỏ dở hoàn toàn kết quả của 10 câu khó nhất.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Lỗi cơ bản nằm ở môi trường Windows. Các kết xuất đầu ra của LLM về `route_reason` và `final_answer` có chứa kí tự Tiếng Việt (Ví dụ: "chính sách hoàn tiền"). Hàm `open()` trong thư viện gốc của Python trên hệ điều hành này dùng chuẩn mã hóa `cp1252` thay vì `utf-8` gây lỗi xung đột khi gặp "dấu".

**Cách sửa:**
- Xuyên suốt `eval_trace.py`, rà soát tất cả các điểm mở file read/write (như hàm `write_jsonl`, `load_jsonl`).
- Bơm thêm cờ cứng: `encoding='utf-8'`.

**Bằng chứng trước/sau:**
- Trước: `UnicodeDecodeError: 'charmap' codec can't decode...`
- Sau: Script thu thập thành công 10/10 traces và in ra terminal bảng thống kê mượt mà.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tổng hợp dữ liệu thô và tài liệu hóa số liệu. Mọi dữ kiện rời rạc từ code của các bạn đã được tôi chạy qua `eval_trace.py` để trích xuất ra các chỉ số chứng minh sự vượt trội của hệ thống. Đồng thời tôi đã lọc ra được những "viên ngọc" như case Routing phức tạp `gq09` và `gq07` để phân bổ vào đúng 2 file `routing_decisions.md` và `single_vs_multi_comparison.md`.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tính tự động hóa. Tôi chưa viết được Script CI/CD tự động kích hoạt `eval_trace` mỗi khi có thành viên Push code mới lên Repo mà vẫn phải nhắc nhở bằng lời.

**Nhóm phụ thuộc vào tôi ở đâu?** 
Đầu ra. Nếu Trace bị lỗi hoặc thiếu bằng chứng, toàn bộ điểm của nhóm sẽ bị đánh rớt dù code chạy rất hay.

**Phần tôi phụ thuộc vào thành viên khác:** 
Tôi phụ thuộc vào tính ổn định của `AgentState` từ Duy. Nếu YAML Contract thay đổi đột ngột giữa chừng gây thiếu key như `mcp_tools_used`, code của tôi sẽ phân tích sai 100%.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ tích hợp ngay các công cụ chuyên dụng như **LangSmith** hoặc **Phoenix (Arize)** thay vì tự xây script ghi file JSON thủ công bằng Python như hiện tại. Nhìn vào trace của câu `gq09`, luồng đi của đồ thị có hai bước chuyển liên tiếp (Policy -> Retrieval). Nếu dùng công cụ Dashboard UI có kéo thả, tôi và team có thể tận mắt xem rõ đường di chuyển của Node, trực quan hóa được ngay lập tức Nút cổ chai (Bottleneck) độ trễ nằm ở đâu để tối ưu thay vì đọc JSON chay.
