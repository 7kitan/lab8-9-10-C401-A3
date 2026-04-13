# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Đức Duy  
**Vai trò trong nhóm:** Retrieval Owner + Documentation Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi chịu trách nhiệm chính trong **Sprint 3** (Tuning) và **Sprint 4** (Documentation). Cụ thể, tôi đã implement ba hàm cốt lõi trong file `rag_answer.py`: (1) `retrieve_sparse()` — sử dụng thư viện `rank-bm25` để tạo BM25 index từ toàn bộ corpus trong ChromaDB, phục vụ keyword matching; (2) `retrieve_hybrid()` — kết hợp Dense Retrieval với Sparse Retrieval bằng thuật toán Reciprocal Rank Fusion (RRF), trọng số `dense_weight=0.6`, `sparse_weight=0.4`; và (3) `rerank()` — sử dụng Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) để chấm điểm lại top candidates, lọc ra chunk thực sự liên quan nhất trước khi đưa vào LLM.

Về documentation, tôi viết toàn bộ file `docs/tuning-log.md` — ghi lại kết quả baseline, phân tích per-question, xây dựng Error Tree để xác định bottleneck, và so sánh A/B giữa baseline vs variant. Công việc của tôi kết nối trực tiếp với phần indexing (Sprint 1) của Tech Lead và phần eval (Sprint 4) của Eval Owner.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu sâu hơn hai concept chính: **Hybrid Retrieval + Rerank pipeline** và **A/B evaluation discipline**.

Về Hybrid + Rerank: trước khi làm lab, tôi nghĩ Dense search đã đủ mạnh vì nó hiểu "ý nghĩa" câu hỏi. Nhưng khi test với các query chứa mã kỹ thuật như "SLA P1" hay "ERR-403", Dense search trả về chunk có ngữ nghĩa gần nhưng không chứa chính xác từ khóa cần tìm. BM25 bổ trợ ở điểm này — nó tìm theo exact term matching. RRF gộp hai danh sách kết quả dựa trên **thứ hạng** chứ không phải score tuyệt đối. Tuy nhiên, chỉ Hybrid chưa đủ — bước Rerank bằng Cross-Encoder mới thực sự tạo ra khác biệt: nó "nhìn" cả query lẫn chunk cùng lúc để đánh giá mức độ liên quan, thay vì chỉ dựa vào embedding similarity đơn chiều.

Về A/B discipline: quy tắc "chỉ đổi MỘT biến mỗi lần" nghe đơn giản nhưng rất khó thực hành. Khi viết tuning log, tôi phải phân tích từng câu hỏi để xác định rõ cải thiện (nếu có) đến từ đâu — retrieval hay generation — chứ không chỉ nhìn average score.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên lớn nhất là **Context Recall đã đạt 5.0/5 ngay từ baseline**. Tôi kỳ vọng Hybrid sẽ cải thiện recall đáng kể, nhưng thực tế Dense search đã tìm đúng tất cả expected sources. Điều này có nghĩa bottleneck không nằm ở retrieval mà ở generation — LLM tìm được đúng context nhưng không extract hết chi tiết.

Khó khăn lớn nhất là thiết kế RRF fusion. Ban đầu tôi dùng linear combination trực tiếp giữa cosine score và BM25 score, nhưng kết quả rất tệ vì hai scale hoàn toàn khác nhau (cosine từ 0–1, BM25 có thể lên hàng chục). Sau khi nghiên cứu, tôi chuyển sang RRF với công thức `1/(k + rank)` (k=60), chỉ dựa trên thứ hạng thay vì score tuyệt đối. Giả thuyết ban đầu "hybrid sẽ tăng recall mạnh" không đúng, nhưng thực tế hybrid + rerank lại giúp tăng **Completeness** nhờ chọn chunk chất lượng hơn.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq09 — *"Mật khẩu tài khoản công ty cần đổi định kỳ không? Nếu có, hệ thống sẽ nhắc nhở trước bao nhiêu ngày và đổi qua đâu?"*

**Phân tích:**

Baseline trả lời **đúng phần chính** (đổi mỗi 90 ngày, nhắc nhở 7 ngày trước) nhưng **thiếu kênh đổi mật khẩu** (SSO portal `https://sso.company.internal/reset` hoặc Helpdesk ext. 9000). Điểm: F=5, R=5, Recall=5, C=3. Lỗi nằm ở **generation layer** — context chunk chứa đầy đủ thông tin nhưng LLM chỉ extract 2/4 chi tiết được hỏi.

Variant (Hybrid + Rerank) cải thiện Completeness từ **3 lên 4**. Rerank đã chọn chunk chứa đầy đủ phần FAQ về mật khẩu (bao gồm cả kênh đổi) thay vì chunk chỉ chứa phần tổng quát. Cross-encoder đánh giá mức độ liên quan giữa query "mật khẩu...đổi qua đâu" và chunk chứa URL/ext. cao hơn chunk chỉ nói về chu kỳ đổi → top-3 chunks được rerank chất lượng hơn → LLM extract thêm chi tiết.

Tuy nhiên, Completeness vẫn chưa đạt 5 — LLM vẫn bỏ sót ext. 9000 dù context có. Đây là minh chứng rõ ràng rằng **prompt engineering** (hướng dẫn LLM liệt kê TẤT CẢ chi tiết) sẽ có tác động lớn hơn việc thay đổi retrieval strategy.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ tập trung vào **Prompt Engineering cho multi-detail extraction**. Evidence từ scorecard cho thấy 8/10 câu đạt Faithfulness = 5 nhưng Completeness ≤ 3 — LLM bám đúng context nhưng bỏ sót chi tiết phụ. Cụ thể, tôi sẽ thêm instruction: *"Liệt kê TẤT CẢ số liệu, ngày tháng, tên người phê duyệt, và kênh liên hệ có trong context"*. Ngoài ra, tôi muốn thiết kế prompt riêng cho trường hợp abstain (gq07) để thay vì nói "Tôi không biết", pipeline sẽ giải thích rõ thông tin nào không tồn tại trong tài liệu.

