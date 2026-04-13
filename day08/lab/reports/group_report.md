# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** Group A03 
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Nguyễn Tuấn Kiệt | Tech Lead | kiet.swe@gmail.com |
| [Tên thành viên] | Retrieval Owner | ___ |
| Nguyễn Văn Bách | Eval Owner | vanbachpk1@gmail.com |
| Nguyễn Đức Duy | Retrieval Owner + Documentation Owner| ducduynguyen1307@gmail.com
| Nguyễn Duy Hưng | Documentation Owner | hungngduy2003@gmail.com |

**Ngày nộp:** 2026-04-13  
**Repo:** https://github.com/7kitan/lab8-9-10-C401-A3.git

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

Nhóm đã xây dựng một pipeline RAG hoàn chỉnh để hỗ trợ tra cứu chính sách nội bộ. Cụ thể:

- **Chunking strategy:** Nhóm sử dụng kích thước chunk là **400 tokens** với overlap là **80 tokens**. Phương pháp tách dựa trên **Heading-based** (tách theo các tiêu đề "=== Section ===") giúp giữ nguyên cấu trúc logic của văn bản, tránh việc một điều khoản bị cắt đôi giữa các chunk.
- **Embedding model:** Sử dụng model `text-embedding-3-small` của OpenAI để tạo vector representation cho các chunk.
- **Retrieval mode:** Trong phiên bản Variant (Sprint 3), nhóm đã triển khai chế độ **Hybrid Retrieval** kết hợp giữa Dense search (semantic) và Sparse search (BM25 - keyword) thông qua thuật toán RRF. Ngoài ra, nhóm còn tích hợp thêm bước **Rerank** sử dụng Cross-encoder (`ms-marco-MiniLM-L-6-v2`) để tối ưu hóa thứ hạng các chunk trước khi đưa vào LLM.

**Chunking decision:**
Nhóm chọn `chunk_size=400` và `overlap=80` vì tài liệu chính sách có các đoạn văn tương đối dài và chứa nhiều chi tiết kỹ thuật. Việc tách theo section headers giúp mỗi chunk luôn mang đầy đủ ngữ cảnh của một mục cụ thể (ví dụ: mục Hoàn tiền, mục SLA).

**Embedding model:**
OpenAI `text-embedding-3-small` được chọn vì hiệu năng ổn định, chi phí thấp và hỗ trợ tốt cho các truy vấn bằng cả tiếng Anh lẫn tiếng Việt trong corpus.

**Retrieval variant (Sprint 3):**
Nhóm chọn **Hybrid + Rerank**. Lý do là corpus chứa nhiều thuật ngữ đặc thù (mã lỗi ERR-403, mức độ P1, P2) mà Dense search đôi khi không bắt chính xác bằng BM25. Bước Rerank giúp lọc ra top 3 chunk thực sự liên quan nhất từ pool 10 candidate ban đầu.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Nâng cấp từ Baseline (Dense only) lên Variant (Hybrid + Rerank).

**Bối cảnh vấn đề:**
Trong quá trình thử nghiệm Baseline, nhóm nhận thấy một số câu hỏi chứa từ khóa viết tắt hoặc mã định danh (ví dụ: "SLA P1", "Approval Matrix") thường bị mô hình Dense search trả về kết quả có độ tương đồng ngữ nghĩa cao nhưng không chứa chính xác từ khóa cần tìm, dẫn đến tình trạng LLM không đủ dữ liệu để trả lời (abstain) hoặc trả lời thiếu chi tiết.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Dense only (Baseline) | Đơn giản, tốc độ nhanh, hiểu ngữ nghĩa tốt. | Hay bỏ lỡ các keyword chính xác hoặc mã lỗi. |
| Hybrid (Dense + BM25) | Kết hợp được cả semantic và keyword matching. | Cần điều chỉnh trọng số (alpha) giữa 2 nguồn. |
| Hybrid + Rerank | Tối ưu hóa cực tốt thứ hạng chunk relevant nhất. | Tốn thêm thời gian xử lý (latency) cho bước cross-encoder. |

**Phương án đã chọn và lý do:**
Nhóm chọn **Hybrid + Rerank**. Quyết định này dựa trên đặc thù của corpus là tài liệu kỹ thuật và chính sách. Việc kết hợp BM25 giúp đảm bảo các keyword quan trọng luôn được tìm thấy, và Cross-encoder đóng vai trò "người thẩm định cuối cùng" để đảm bảo context truyền vào LLM là chất lượng nhất.

**Bằng chứng từ scorecard/tuning-log:**
Kết quả chạy A/B cho thấy metric **Completeness** tăng từ **3.00 lên 3.20**. Đặc biệt ở câu gq09 (về mật khẩu), Rerank đã giúp chọn đúng chunk chứa đầy đủ chi tiết về quy trình đổi mật khẩu, giúp LLM cung cấp câu trả lời trọn vẹn hơn.

---

## 3. Kết quả grading questions (100–150 từ)

Sau khi chạy pipeline với `grading_questions.json`:

- **Câu tốt nhất:** **ID: gq06** và **gq08**. Cả hai đều đạt điểm Faithfulness, Relevance và Recall tuyệt đối (5/5), đồng thời Completeness đạt 4/5. Lý do là context được retrieve rất sát và LLM trích xuất được hầu hết các chi tiết quan trọng (thời gian remote, quy trình escalate).
- **Câu fail:** **ID: gq07** (về mức phạt SLA P1). Đây là câu hỏi "bẫy" (abstain bait) vì thông tin mức phạt không có trong tài liệu. Pipeline trả lời "Tôi không biết" - đúng về mặt grounding nhưng lại bị điểm thấp ở Faithfulness/Relevance (1/1) vì không giải thích rõ là tài liệu thiếu thông tin.
- **Câu gq07 (abstain):** Pipeline xử lý bằng cách trả về câu trả lời mặc định "Tôi không biết". Đây là lỗi ở tầng Generation layer - prompt chưa được tinh chỉnh để xử lý các trường hợp "không tìm thấy thông tin" một cách khéo léo.

**Ước tính điểm raw:** 84 / 98 (Dựa trên trung bình các metric 4.6/5 trừ đi điểm trừ ở các câu Completeness thấp và câu gq07).

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

Dựa vào `docs/tuning-log.md`, nhóm tóm tắt kết quả so sánh:

**Biến đã thay đổi (chỉ 1 biến):** Chế độ Retrieval (từ Dense sang Hybrid + Rerank).

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.60 | 4.60 | 0.00 |
| Answer Relevance | 4.60 | 4.60 | 0.00 |
| Context Recall | 5.00 | 5.00 | 0.00 |
| Completeness | 3.00 | 3.20 | +0.20 |

**Kết luận:**
Variant tốt hơn Baseline ở khía cạnh **Completeness (+0.20)**. Việc kết hợp Hybrid và Rerank không làm giảm độ chính xác (Faithfulness) hay độ liên quan (Relevance) nhưng đã giúp LLM tiếp cận được những chunk "đắt" giá hơn, từ đó trích xuất được nhiều chi tiết phụ hơn cho câu trả lời. Tuy nhiên, Delta không quá lớn do bottleneck hiện tại nằm ở khả năng extract của LLM hơn là chất lượng retrieval.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

Quá trình làm việc nhóm diễn ra khá nhịp nhàng dù các sprint đòi hỏi tốc độ cao.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nguyễn Tuấn Kiệt | Tech Lead - Nối code, config API | 1, 2 |
| [Tên thành viên] | Retrieval Owner - Chunking, Rerank | 1, 3 |
| Nguyễn Văn Bách | Eval Owner - Scorecard, A/B Test | 3 |
| Nguyễn Đức Duy | retrieval strategy, Tuning Log | 3, 4 |
| Nguyễn Duy Hưng | Documentation Owner - Architecture, Tuning Log, Group Report | 4 |

**Điều nhóm làm tốt:**
- Phân chia vai trò rõ ràng ngay từ đầu.
- Tài liệu hóa (documentation) được thực hiện song song với code giúp việc viết báo cáo cuối cùng rất nhanh chóng.
- Hệ thống retrieval đạt Context Recall tuyệt đối (5.0/5).

**Điều nhóm làm chưa tốt:**
- Chưa tối ưu được Prompt Engineering để giải quyết triệt để lỗi Completeness và cách xử lý Abstain (gq07).
- Quá trình tuning alpha cho Hybrid mất nhiều thời gian hơn dự kiến.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ tập trung vào **Prompt Tuning** cho tầng Generation. Bằng chứng từ scorecard cho thấy Retrieval đã rất tốt (Recall 5.0), nhưng Completeness vẫn là bottleneck (3.2). Chúng tôi sẽ thử hướng dẫn explicit hơn trong prompt: "Liệt kê tất cả các số liệu, ngày tháng và đối tượng phê duyệt có trong context", đồng thời cải thiện template trả lời cho các câu hỏi thiếu dữ liệu để tăng điểm gq07.

---

*File này được hoàn thiện bởi Nguyễn Duy Hưng (Documentation Owner) cho Lab Day 08.*
