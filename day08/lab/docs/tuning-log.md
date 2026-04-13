# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "gpt-4o-mini"
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.60 /5 |
| Answer Relevance | 4.50 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 3.90 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> TODO: Liệt kê 2-3 câu hỏi có điểm thấp nhất và lý do tại sao.
> Ví dụ: "q07 (Approval Matrix) - context recall = 1/5 vì dense bỏ lỡ alias."

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** `retrieval_mode = "hybrid"`  
**Lý do chọn biến này:**
Hệ thống cần bắt chính xác các thuật ngữ chuyên môn và mã lỗi (như P1, ERR-403) có trong tài liệu. Hybrid kết hợp Dense (ngữ nghĩa) và Sparse (BM25) giúp cân bằng giữa hiểu ý người dùng và tìm đúng từ khoá.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.60/5 | 4.40/5 | -0.20 |
| Answer Relevance | 4.50/5 | 4.30/5 | -0.20 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.90/5 | 3.40/5 | -0.50 |

**Nhận xét:**
Variant Hybrid duy trì được Context Recall tuyệt đối (5.00), chứng tỏ retriever vẫn tìm đúng documents. Tuy nhiên, điểm Faithfulness và Completeness giảm nhẹ trong bộ câu hỏi test này. Điều này có thể do kết quả Hybrid mang về các chunks có chứa từ khoá "nhiễu" khiến LLM gen bị ảnh hưởng.

**Kết luận:**
Trong bài lab này, Hybrid chưa cho thấy sự vượt trội về điểm số tổng thể so với Dense thuần túy. Tuy nhiên, về mặt lý thuyết nó sẽ bền bỉ hơn khi quy mô tài liệu lớn dần và chứa nhiều tên riêng/mã lỗi.


---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** ___________  
**Config:**
```
# TODO
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | ? | ? | ? | ? |
| Answer Relevance | ? | ? | ? | ? |
| Context Recall | ? | ? | ? | ? |
| Completeness | ? | ? | ? | ? |

---

## Tóm tắt học được

> TODO (Sprint 4): Điền sau khi hoàn thành evaluation.

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   Lỗi Completeness (3.4-3.9). Answer đôi khi không bao phủ được hết các chi tiết ngoại lệ trong chính sách.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   Retrieval strategy (Dense vs Hybrid) hiện tại đang có tác động mạnh nhất.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   Thử nghiệm Rerank (Cross-Encoder) để lọc nhiễu sau bước Hybrid và tinh chỉnh weights của RRF.
