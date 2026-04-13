# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Xuân Hoàng  
**Vai trò trong nhóm:** Retrieval Owner  
**Nhóm:** Group A03  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong bài lab Day 08 này, tôi đảm nhận vai trò **Retrieval Owner**, chịu trách nhiệm xây dựng và tối ưu hóa toàn bộ pipeline tìm kiếm từ Sprint 1 đến Sprint 3.

- **Sprint 1 — Chunking & Indexing:** Tôi quyết định và triển khai chiến lược chunking cho tất cả 5 tài liệu chính sách. Cụ thể, tôi chọn `chunk_size = 400 tokens`, `overlap = 80 tokens`, tách theo **Heading-based** (dựa trên các dấu phân cách `=== Section ===`) để đảm bảo mỗi chunk giữ nguyên cấu trúc logic của một mục chính sách, tránh cắt đôi điều khoản.

- **Sprint 3 — Hybrid Retrieval + Rerank:** Tôi nâng cấp từ Dense search (baseline) sang **Hybrid Retrieval** bằng cách kết hợp vector search (ChromaDB cosine similarity) với BM25 keyword matching thông qua thuật toán **Reciprocal Rank Fusion (RRF)**. Ngoài ra, tôi tích hợp bước **Rerank** sử dụng Cross-Encoder `ms-marco-MiniLM-L-6-v2` để lọc lấy top 3 chunk chất lượng nhất từ pool 10 candidates trước khi đưa vào LLM.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau bài lab này, tôi hiểu sâu hơn về lý do thực sự cần **Hybrid Retrieval** trong các corpus tài liệu kỹ thuật nội bộ.

Trước khi làm lab, tôi nghĩ Dense search (embedding similarity) là đủ mạnh vì nó biết "hiểu nghĩa" câu hỏi. Nhưng khi corpus chứa các thuật ngữ kỹ thuật kiểu như "SLA P1", "ERR-403-AUTH", hay "Level 3 access" — những từ có ý nghĩa rất cụ thể về mặt kỹ thuật — thì Dense search đôi khi trả về các chunk "gần nghĩa" nhưng không chứa đúng từ khóa. BM25 bổ trợ chính xác ở điểm này: nó match theo ký tự chính xác, không phụ thuộc vào embedding.

Điều thứ hai tôi hiểu rõ hơn là về **Cross-Encoder Reranking**: khác với Bi-Encoder (tạo embedding riêng lẻ cho query và chunk rồi so sánh), Cross-Encoder nhìn cả query lẫn chunk cùng lúc trong một lần forward pass, từ đó đánh giá mức độ liên quan chính xác hơn đáng kể, dù tốc độ chậm hơn.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến tôi bất ngờ là kết quả Context Recall đạt 5.00/5 ngay từ baseline Dense search. Tôi kỳ vọng rằng Hybrid sẽ cải thiện recall đáng kể — nhưng thực tế Dense đã tìm đúng tất cả expected sources. Điều này có nghĩa bottleneck không nằm ở retrieval mà ở generation layer — LLM tìm được đúng nguồn nhưng không extract hết tất cả chi tiết từ context.

Khó khăn lớn nhất tôi gặp là việc điều chỉnh trọng số giữa Dense và BM25 trong Hybrid. Ban đầu tôi thử cộng score trực tiếp (linear combination) nhưng kết quả không ổn vì hai scale hoàn toàn khác nhau — cosine similarity dao động 0–1 còn BM25 score có thể lên đến hàng chục tùy corpus. Giải pháp cuối cùng là dùng **RRF** (`1/(k + rank)`, k=60) chỉ dựa trên *thứ hạng* chứ không phải score tuyệt đối — cách này robust hơn nhiều và không cần căn chỉnh scale.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq09 — *"Mật khẩu tài khoản công ty cần đổi định kỳ không? Nếu có, hệ thống sẽ nhắc nhở trước bao nhiêu ngày và đổi qua đâu?"*

**Phân tích:**

Đây là câu hỏi cho thấy rõ nhất tác dụng của bước **Rerank** mà tôi đã triển khai.

Với **Baseline (Dense only)**: hệ thống retrieve được chunk nói về chu kỳ đổi mật khẩu (90 ngày) và thời gian nhắc nhở (7 ngày), nhưng bỏ lỡ phần chi tiết kênh đổi mật khẩu (SSO portal hoặc Helpdesk ext. 9000). Kết quả: `F=5, R=5, Recall=5, C=3` — trả lời đúng nhưng thiếu chi tiết.

Với **Variant (Hybrid + Rerank)**: Cross-Encoder đã ưu tiên chọn chunk FAQ về mật khẩu — chunk này chứa đầy đủ cả thông tin chu kỳ lẫn kênh đổi — thay vì chunk tổng quát hơn. Kết quả: `C tăng từ 3 lên 4`. Việc rerank nhìn toàn bộ câu hỏi (bao gồm từ "đổi qua đâu") cùng với chunk cho phép nó đánh trọng số cao hơn cho chunk chứa URL/số điện thoại → LLM extract được thêm thông tin.

Câu này chứng minh Rerank có giá trị thực tế — không chỉ là kỹ thuật lý thuyết.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ tập trung vào **Prompt Engineering cho completeness** thay vì tối ưu thêm retrieval. Evidence từ scorecard rất rõ ràng: Recall đã đạt 5.0/5, nghĩa là retrieval không còn là bottleneck. 8/10 câu hỏi đạt Faithfulness = 5 nhưng Completeness chỉ ≤ 3 — LLM bám đúng context nhưng không extract hết chi tiết phụ. Tôi sẽ thử thêm instruction vào prompt: *"Liệt kê TẤT CẢ số liệu, ngày tháng, tên người phê duyệt, kênh liên hệ có trong context"*, và thiết kế template riêng cho trường hợp abstain (gq07) để pipeline giải thích rõ thông tin nào không tồn tại trong tài liệu thay vì chỉ nói "Tôi không biết".

---
