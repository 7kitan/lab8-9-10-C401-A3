# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Duy Hưng  
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 2026-04-13  

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong dự án lab này, với vai trò là **Documentation Owner**, tôi chịu trách nhiệm chính trong việc chuẩn hóa hệ thống tài liệu kỹ thuật và ghi chép lại mọi quyết định thiết kế của nhóm. Tôi tập trung chủ yếu vào Sprint 4, nơi tôi phải tổng hợp các kết quả từ các giai đoạn Indexing, Retrieval và Generation để hoàn thiện file `architecture.md` và `group_report.md`.

Cụ thể, tôi đã phối hợp chặt chẽ với Tech Lead để hiểu rõ luồng dữ liệu từ lúc tiền xử lý văn bản đến khi lưu trữ trong ChromaDB. Tôi cũng làm việc với Retrieval Owner để ghi lại các thay đổi trong chiến lược tìm kiếm (từ Dense sang Hybrid) và với Eval Owner để phân tích các failure modes thường gặp. Công việc của tôi đóng vai trò là "chất keo" kết nối các module rời rạc thành một hệ thống có tính hệ thống cao, giúp các thành viên khác dễ dàng debug và theo dõi quá trình A/B testing của nhóm.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi đã hiểu sâu sắc hơn về **kiến trúc RAG Pipeline** và tầm quan trọng của việc **phân tích Failure Modes**. Trước đây, tôi chỉ nghĩ RAG đơn giản là "nhét dữ liệu vào vector database rồi hỏi". Tuy nhiên, qua việc xây dựng tài liệu kiến trúc, tôi nhận ra hệ thống có thể "gãy" ở bất kỳ công đoạn nào: từ việc chunking sai làm mất ngữ cảnh, đến việc retrieval không fetch được đúng tài liệu cần thiết (context recall thấp), hay LLM bị "ảo giác" (low faithfulness) dù context đã đủ.

Việc viết ra sơ đồ Mermaid và bảng Failure Mode Checklist giúp tôi định hình rõ ràng các điểm mù trong hệ thống. Tôi học được rằng một hệ thống AI tốt không chỉ ở kết quả cuối cùng, mà còn ở khả năng quan sát (observability) và khả năng giải trình (traceability) thông qua các trích dẫn (citations) và trắc nghiệm mức độ tin cậy của câu trả lời.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến tôi ngạc nhiên nhất là sức mạnh của **Hybrid Retrieval** so với chỉ dùng Dense Retrieval truyền thống. Ban đầu, tôi giả định rằng các mô hình embedding hiện đại (như `text-embedding-3-small`) đã đủ "thông minh" để hiểu mọi ngữ nghĩa. Tuy nhiên, thực tế debug cho thấy với các query chứa alias hoặc mã lỗi cụ thể (như "ERR-403" hay "Approval Matrix"), Dense search đôi khi trả về những đoạn văn bản trông có vẻ liên quan về mặt từ ngữ nhưng lại sai hoàn toàn về mặt kỹ thuật.

Khó khăn lớn nhất tôi gặp phải là làm thế nào để mô tả các trade-offs một cách súc tích trong `tuning-log.md`. Việc quyết định chọn Variant (Hybrid + Rerank) thay vì Baseline đòi hỏi phải có bằng chứng từ scorecard, và việc "chuyển ngữ" các con số khô khan thành những nhận định kiến trúc có giá trị là một thách thức không nhỏ. Tôi đã mất khá nhiều thời gian để tinh chỉnh sơ đồ luồng dữ liệu sao cho phản ánh đúng sự khác biệt giữa hai giai đoạn tìm kiếm.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** "Approval Matrix để cấp quyền hệ thống là tài liệu nào?" (ID: q07)

**Phân tích:**
Đây là một câu hỏi thuộc mức độ "Khó" vì nó yêu cầu hệ thống phải hiểu được sự thay đổi về tên gọi của tài liệu. Trong thực tế, tài liệu mang tên cũ là "Approval Matrix for System Access" nhưng hiện tại đã được đổi tên thành "Access Control SOP".

- **Baseline:** Khi sử dụng Dense Retrieval thuần túy, hệ thống gặp khó khăn vì query chứa cụm từ "Approval Matrix" - một từ khóa không xuất hiện nhiều trong nội dung mới của SOP. Kết quả là Baseline trả về điểm context recall thấp và câu trả lời thường là "Tôi không tìm thấy thông tin cụ thể về Approval Matrix".
- **Lỗi nằm ở:** **Retrieval**. Vector embedding của query không đủ gần với vector của chunk chứa thông tin mapping tên cũ-mới trong không gian ngữ nghĩa của mô hình OpenAI.
- **Variant:** Sau khi áp dụng **Hybrid Retrieval (kết hợp BM25)**, hệ thống đã bắt được keyword "Approval Matrix" có trong phần metadata hoặc đoạn giới thiệu của file `access-control-sop.md`. Việc cộng thêm điểm từ BM25 giúp chunk này nổi lên top đầu.
- **Kết quả:** Variant trả lời chính xác ID q07, chỉ ra rõ tài liệu mới là `access-control-sop.md`. Điều này chứng minh rằng với các corpus chứa nhiều thuật ngữ chuyên môn hoặc alias, Hybrid là một phần kiến trúc không thể thiếu.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thử nghiệm việc **tự động hóa (Automated Documentation)** bằng cách tích hợp trực tiếp kết quả từ `eval.py` vào `tuning-log.md`. Hiện tại, việc sao chép thủ công các số liệu scorecard khá mất thời gian và dễ sai sót. Tôi muốn viết một script nhỏ để tự động sinh ra các bảng so sánh Delta giữa Baseline và Variant mỗi khi team chạy evaluation. Điều này sẽ giúp Documentation Owner tập trung vào việc phân tích "Tại sao" thay vì chỉ loay hoay với "Con số là gì".

---

*File này được hoàn thiện bởi Documentation Owner dựa trên template báo cáo cá nhân.*
