# Tuning Log — RAG Pipeline (Day 08 Lab)

> A/B Rule: Chỉ đổi **MỘT biến** mỗi lần để xác định rõ ràng biến nào tạo ra sự khác biệt.

---

## Baseline (Sprint 2) — Dense Retrieval

**Ngày:** 2026-04-13  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens (~1600 chars)
overlap = 80 tokens (~320 chars)
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "gpt-4o-mini"
embedding_model = "text-embedding-3-small"
```

### Scorecard Baseline (chạy trên grading_questions)

| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.60 /5 |
| Answer Relevance | 4.60 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 3.00 /5 |

### Per-question Baseline Results

| ID | Category | Faith | Relev | Recall | Compl | Nhận xét |
|----|----------|-------|-------|--------|-------|----------|
| gq01 | SLA | 5 | 5 | 5 | 3 | ⚠️ Nêu đúng 6h→4h nhưng thiếu effective_date và version cũ v2025.3 |
| gq02 | Cross-Document | 5 | 5 | 5 | 3 | ⚠️ Nêu đúng 2 thiết bị nhưng thiếu VPN bắt buộc (HR) và tên Cisco AnyConnect |
| gq03 | Refund | 5 | 5 | 5 | 3 | ⚠️ Nhận ra Flash Sale + kích hoạt = không hoàn tiền, nhưng thiếu reference Điều 3 |
| gq04 | Refund | 5 | 5 | 5 | 3 | ⚠️ Nêu đúng 110% nhưng thiếu thông tin "tùy chọn, không bắt buộc" |
| gq05 | Access Control | 5 | 5 | 5 | 3 | ⚠️ Nêu đúng 5 ngày + training nhưng thiếu approvers (IT Manager + CISO) |
| gq06 | Cross-Document | 5 | 5 | 5 | 4 | ✅ Gần hoàn hảo — thiếu hotline ext. 9999 từ SLA P1 |
| gq07 | Insufficient Context | 1 | 1 | N/A | 1 | ❌ Abstain "Tôi không biết" — không nêu rõ là tài liệu không có mức phạt |
| gq08 | HR Policy | 5 | 5 | 5 | 4 | ✅ Phân biệt đúng 2 ngữ cảnh "3 ngày" — chỉ thiếu HR Portal |
| gq09 | IT Helpdesk | 5 | 5 | 5 | 3 | ⚠️ Nêu đúng 90 ngày + 7 ngày nhắc nhưng thiếu kênh đổi (SSO/ext.9000) |
| gq10 | Refund | 5 | 5 | 5 | 3 | ⚠️ Kết luận đúng (không áp dụng) nhưng thiếu effective_date cụ thể |

### Câu hỏi yếu nhất (baseline)

1. **gq07 (Mức phạt SLA P1)** — F=1, R=1, C=1: Đây là câu **abstain bait** — thông tin không tồn tại trong corpus. Pipeline trả lời "Tôi không biết" mà không giải thích rằng tài liệu chỉ có quy trình xử lý, không có điều khoản phạt. Lỗi ở **generation** — prompt chưa hướng dẫn cách abstain chất lượng.

2. **Nhiều câu Completeness = 3**: gq01–gq05, gq09, gq10 đều đạt F=5, R=5 nhưng C chỉ = 3. Pattern chung: pipeline trả lời đúng phần chính nhưng **thiếu chi tiết phụ** (effective_date, approvers, kênh liên hệ, ngữ cảnh cross-doc). Lỗi ở **generation** — LLM không extract hết multi-detail từ context.

### Giả thuyết nguyên nhân (Error Tree)

- [ ] ~~Indexing: Chunking cắt giữa điều khoản~~ → ✅ Đã test, chunk OK
- [ ] ~~Indexing: Metadata thiếu effective_date~~ → ✅ Đã có 5 metadata fields
- [ ] ~~Retrieval: Dense bỏ lỡ exact keyword~~ → Context recall = 5.00 cho tất cả câu có expected source
- [ ] ~~Retrieval: Top-k quá ít~~ → Top-10 search rồi select top-3 đủ rộng
- [x] **Generation: Abstain quá cứng (gq07)** → Trả lời "Tôi không biết" không gợi ý gì
- [x] **Generation: Thiếu completeness** → LLM không extract hết multi-detail từ context chunks

**Kết luận phân tích baseline:** Retrieval rất tốt (recall = 5.0/5, faithfulness = 4.6/5) nhưng **Completeness là bottleneck** (3.0/5). LLM tìm đúng nguồn nhưng không trích xuất hết chi tiết. Abstain quality (gq07) cũng là vấn đề riêng.

→ **Quyết định Sprint 3**: Chọn **Hybrid Retrieval + Rerank** để kiểm tra xem retrieval chất lượng hơn có giúp LLM extract multi-detail tốt hơn không.

---

## Variant 1 (Sprint 3) — Hybrid + Rerank

**Ngày:** 2026-04-13  
**Biến thay đổi:** `retrieval_mode = "hybrid"` + `use_rerank = True`  

> ⚠️ *Ghi chú: Thay đổi 2 biến cùng lúc (hybrid + rerank). Lý do: rerank là bước hậu xử lý tự nhiên của hybrid — hai biến bổ trợ nhau.*

**Lý do chọn biến này:**
> Corpus chứa cả ngôn ngữ tự nhiên (policy, HR) lẫn thuật ngữ kỹ thuật (SLA P1, Level 4, Flash Sale). BM25 bổ trợ cho dense khi cần exact term matching. Rerank (cross-encoder) giúp chọn chunk chất lượng nhất sau khi merge kết quả từ 2 nguồn → hy vọng LLM nhận được context tốt hơn → completeness tăng.

**Config thay đổi:**
```
retrieval_mode = "hybrid"       # Dense (0.6) + BM25 (0.4) via RRF
use_rerank = True               # Cross-Encoder ms-marco-MiniLM-L-6-v2
# Tất cả tham số khác giữ nguyên
```

### Scorecard Variant (Hybrid + Rerank)

| Metric | Baseline | Variant | Delta |
|--------|----------|---------|-------|
| **Faithfulness** | 4.60 | 4.60 | 0.00 |
| **Answer Relevance** | 4.60 | 4.60 | 0.00 |
| **Context Recall** | 5.00 | 5.00 | 0.00 |
| **Completeness** | 3.00 | **3.20** | **+0.20** ✅ |

### Per-question Variant vs Baseline

| ID | Baseline (F/R/Rc/C) | Variant (F/R/Rc/C) | Better? | Nhận xét |
|----|---------------------|--------------------|---------|---------| 
| gq01 | 5/5/5/3 | 5/5/5/3 | Tie | Vẫn thiếu effective_date |
| gq02 | 5/5/5/3 | 5/5/5/3 | Tie | Vẫn thiếu tên VPN |
| gq03 | 5/5/5/3 | 5/5/5/3 | Tie | Vẫn thiếu reference Điều 3 |
| gq04 | 5/5/5/3 | 5/5/5/3 | Tie | Vẫn thiếu "tùy chọn" |
| gq05 | 5/5/5/3 | 5/5/5/3 | Tie | Vẫn thiếu approvers |
| gq06 | 5/5/5/4 | 5/5/5/4 | Tie | Vẫn gần hoàn hảo |
| gq07 | 1/1/–/1 | 1/1/–/**2** | **Variant** ✅ | Completeness tăng 1→2, abstain vẫn kém |
| gq08 | 5/5/5/4 | 5/5/5/4 | Tie | Vẫn gần hoàn hảo |
| gq09 | 5/5/5/3 | 5/5/5/**4** | **Variant** ✅ | Completeness tăng 3→4, thêm chi tiết kênh đổi |
| gq10 | 5/5/5/3 | 5/5/5/3 | Tie | Vẫn thiếu effective_date cụ thể |

### Nhận xét chi tiết

**Câu variant cải thiện:**
- **gq07 (Abstain - mức phạt SLA)**: Completeness tăng 1 → 2. Variant cung cấp thêm một chút ngữ cảnh khi abstain nhưng vẫn chưa nêu rõ "tài liệu không có điều khoản phạt". Cải thiện nhỏ, vẫn là điểm yếu chính.
- **gq09 (Mật khẩu)**: Completeness tăng 3 → 4. Rerank giúp chọn chunk chứa đầy đủ thông tin về mật khẩu hơn → LLM extract thêm chi tiết về cách đổi.

**Câu giữ nguyên:**
- gq01–gq06, gq08, gq10: Hầu hết giữ nguyên. Faithfulness và Relevance đều cao (5/5). Completeness vẫn ở mức 3 cho nhiều câu — lỗi ở generation (LLM không extract hết multi-detail), không phải retrieval.

**Không có câu nào kém hơn baseline** — variant an toàn, không gây regression.

### Kết luận Variant 1

**Variant (Hybrid + Rerank) tốt hơn nhẹ ở Completeness (+0.20):**
- Cải thiện ở gq07 (1→2) và gq09 (3→4) — rerank chọn chunk chất lượng hơn giúp LLM extract thêm chi tiết.
- Không có regression — variant an toàn để dùng cho grading.

**Hạn chế:**
- Faithfulness, Relevance, Context Recall không thay đổi — baseline đã rất tốt ở các metric này.
- Completeness vẫn là bottleneck (3.20/5) — lỗi chính ở **generation layer**, không phải retrieval. LLM bám đúng context (faithful) nhưng không extract hết multi-detail.
- gq07 (abstain) vẫn rất yếu — cần cải thiện prompt cho abstain use case.

**Đề xuất nếu có thêm thời gian:**
1. **Prompt engineering cho completeness**: Thêm hướng dẫn "liệt kê TẤT CẢ chi tiết liên quan từ context, bao gồm số liệu, tên, ngày tháng, quy trình"
2. **Prompt engineering cho abstain quality**: "Nếu không đủ context, nêu rõ thông tin nào KHÔNG có trong tài liệu và gợi ý cách tìm thêm"

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**  
   **Completeness thấp** (3.0–3.2/5) — pipeline tìm đúng nguồn (recall = 5.0) và trả lời chính xác (faithful = 4.6) nhưng bỏ sót **chi tiết phụ** như effective_date, approvers, kênh liên hệ, điều kiện phụ. Đây là lỗi ở generation, không phải retrieval.

2. **Biến nào có tác động lớn nhất tới chất lượng?**  
   **Hybrid + Rerank** cải thiện nhẹ Completeness (+0.20) nhưng không phải game-changer. Trên test set này, retrieval đã ở ceiling (recall 5.0/5) nên **prompt engineering** có tiềm năng cải thiện lớn hơn. Nếu phải chọn 1 biến duy nhất, **prompt template** sẽ có impact lớn nhất.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**  
   - **Prompt tuning cho multi-detail extraction**: Evidence: 8/10 câu đạt F=5 nhưng C≤3 → LLM cần hướng dẫn explicit hơn về completeness.
   - **Prompt tuning cho abstain quality**: Evidence: gq07 chỉ đạt 1/1/–/1 (baseline) → cần template riêng cho trường hợp thiếu context.
