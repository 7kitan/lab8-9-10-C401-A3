# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Xuân Hoàng
**Vai trò trong nhóm:** Worker Owner (Retrieval)
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Mô tả cụ thể module, worker, contract, hoặc phần trace bạn trực tiếp làm.
Không chỉ nói "tôi làm Sprint X" — nói rõ file nào, function nào, quyết định nào.

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/retrieval.py`
- Functions tôi implement: `_get_embedding_fn()`, `_get_collection()`, `retrieve_dense()`, `run()`

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Công việc của tôi nằm ở Phase 2, đóng vai trò là "nguồn kiến thức" cho toàn bộ hệ thống. Sau khi Supervisor (do bạn Duy thực hiện) định tuyến yêu cầu vào `retrieval_worker`, module của tôi sẽ thực nhiệm vụ truy xuất các thông tin liên quan từ ChromaDB. Dữ liệu tôi trả ra (retrieved_chunks) là đầu vào quan trọng bậc nhất để Synthesis Worker (của bạn Kiệt) có thể tổng hợp câu trả lời cuối cùng cho người dùng. Nếu phần của tôi không chạy hoặc trả về kết quả sai, toàn bộ hệ thống sẽ rơi vào trạng thái ảo giác (hallucination) hoặc phải từ chối trả lời (abstain).

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
Các thay đổi trực tiếp trong file `workers/retrieval.py` với cấu trúc hàm `run(state)` tuân thủ chặt chẽ `worker_contracts.yaml`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi chọn triển khai cơ chế **Embedding Fallback** (Kết hợp Sentence Transformers và OpenAI) trong hàm `_get_embedding_fn()`.

**Lý do:**
Trong quá trình phát triển, việc phụ thuộc hoàn toàn vào OpenAI API gây ra hai vấn đề lớn: độ trễ mạng (latency) và chi phí API key khi thực hiện hàng loạt các bài test tự động (grading).
1. **Lựa chọn thay thế:** Chỉ dùng OpenAI hoặc chỉ dùng Random embeddings (chỉ để test code).
2. **Tại sao tôi chọn cách này:** Bằng cách ưu tiên dùng `all-MiniLM-L6-v2` thông qua thư viện `sentence-transformers`, hệ thống có thể chạy hoàn toàn offline với tốc độ cực nhanh (~10-20ms cho một query). Tuy nhiên, tôi vẫn giữ code gọi OpenAI làm fallback để đảm bảo nếu môi trường server không cài được local model, worker vẫn hoạt động được. Điều này giúp `retrieval_worker` trở nên cực kỳ linh hoạt và "stateless" đúng nghĩa.

**Trade-off đã chấp nhận:**
Chấp nhận yêu cầu người dùng phải cài thêm thư viện `sentence-transformers`. Nếu không có thư viện này và cũng không có OpenAI key, worker sẽ phải dùng random embeddings (mức độ degrade cao nhất).

**Bằng chứng từ trace/code:**
```python
def _get_embedding_fn():
    # Option A: Sentence Transformers (offline)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()
        return embed
    except ImportError:
        pass
    # Option B: OpenAI Fallback...
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `ChromaDB collection 'day09_docs' not found` khi chạy integration test lần đầu.

**Symptom (pipeline làm gì sai?):**
Khi Supervisor chuyển task sang Retrieval Worker, hệ thống sập ngay lập tức vì không tìm thấy Collection trong ChromaDB, mặc dù dữ liệu đã được crawl từ Day 08. Toàn bộ StateGraph bị dừng và không thể ghi log I/O.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Lỗi nằm ở việc Worker thiết lập kết nối cứng nhắc. Trong môi trường mới hoặc khi folder `chroma_db` chưa được index đầy đủ bằng script của Day 09, lệnh `client.get_collection` sẽ ném ra ngoại lệ nếu tên collection không khớp chính xác 100%.

**Cách sửa:**
Tôi đã bổ sung logic "Auto-recovery" trong hàm `_get_collection()`. Thay vì chỉ `get_collection`, tôi dùng `try/except` để bắt lỗi và tự động gọi `get_or_create_collection`. Đồng thời, tôi thêm thông báo cảnh báo chi tiết để người dùng biết họ cần chạy script index nếu data đang trống, thay vì để hệ thống crash im lặng.

**Bằng chứng trước/sau:**
- **Trước:** `chromadb.errors.InvalidCollectionException: Collection day09_docs does not exist.`
- **Sau:**
```python
    try:
        collection = client.get_collection("day09_docs")
    except Exception:
        collection = client.get_or_create_collection("day09_docs")
        print(f"Collection 'day09_docs' chưa có data. Chạy index script...")
```
Hệ thống hiện tại sẽ không bao giờ crash tại bước này, nó sẽ trả về empty chunks và log lỗi vào `worker_io_logs` một cách minh bạch.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã xây dựng được một Worker có tính ổn định cao và khả năng test độc lập hoàn hảo. Bằng chứng là phần `if __name__ == "__main__":` ở cuối file cho phép bất kỳ thành viên nào cũng có thể kiểm tra logic truy xuất mà không cần quan tâm đến toàn bộ Graph phức tạp.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi chưa triển khai được **Hybrid Search** (kết hợp BM25 cho keyword và Vector cho semantic). Hiện tại hệ thống thuần Dense Retrieval nên đôi khi gặp khó khăn với các mã lỗi viết tắt (như "err-P1") nếu mô hình embedding không được tinh chỉnh.

**Nhóm phụ thuộc vào tôi ở đâu?**
Sự chính xác. Nếu Retrieval Worker trả về các chunk rác, Synthesis Worker sẽ không có cách nào cứu vãn được chất lượng câu trả lời.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào bạn Duy (Supervisor) để nhận được `task` đã được chuẩn hóa, và phụ thuộc vào script Index dữ liệu của nhóm để đảm bảo ChromaDB có đủ "nguyên liệu" để làm việc.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ tích hợp thêm **Cross-Encoder Reranker** (dùng `cross-encoder/ms-marco-MiniLM-L-6-v2`). Hiện tại tôi lấy top 3 dựa trên cosine similarity, nhưng nếu có thêm bước Rerank, độ chính xác của các đoạn văn bản cung cấp cho Synthesis Worker sẽ cao hơn hẳn, đặc biệt là cho các câu hỏi mang tính so sánh quy định giữa SLA và Policy.

---
