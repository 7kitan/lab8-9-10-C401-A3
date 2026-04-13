"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
Sprint 2 (60 phút): Baseline RAG
  - Dense retrieval từ ChromaDB
  - Grounded answer function với prompt ép citation
  - Trả lời được ít nhất 3 câu hỏi mẫu, output có source

Sprint 3 (60 phút): Tuning tối thiểu
  - Thêm hybrid retrieval (dense + sparse/BM25)
  - Hoặc thêm rerank (cross-encoder)
  - Hoặc thử query transformation (expansion, decomposition, HyDE)
  - Tạo bảng so sánh baseline vs variant

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Tìm kiếm ngữ nghĩa (Dense Retrieval):
    - Sử dụng Vector Similarity để tìm các đoạn văn bản có ý nghĩa gần nhất với câu hỏi.
    - Chuyển đổi Query thành Vector và so sánh với ChromaDB.
    - Hiệu quả với các câu hỏi diễn đạt theo nhiều cách khác nhau nhưng cùng ý nghĩa.
    """
    import chromadb
    from index import get_embedding, CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    if results["documents"]:
        for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
            # distance trong ChromaDB cosine = 1 - similarity
            score = 1.0 - dist
            chunks.append({
                "text": doc,
                "metadata": meta,
                "score": score
            })
    return chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).

    Mạnh ở: exact term, mã lỗi, tên riêng (ví dụ: "ERR-403", "P1", "refund")
    Hay hụt: câu hỏi paraphrase, đồng nghĩa

    TODO Sprint 3 (nếu chọn hybrid):
    1. Cài rank_bm25: pip install rank-bm25
    2. Load tất cả chunks từ ChromaDB (hoặc rebuild từ docs)
    3. Tokenize và tạo BM25Index
    4. Query và trả về top_k kết quả
    """
    from rank_bm25 import BM25Okapi
    import chromadb
    from index import CHROMA_DB_DIR

    # Load all chunks from ChromaDB for BM25
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    all_docs = collection.get(include=["documents", "metadatas"])
    
    if not all_docs["documents"]:
        return []

    corpus = all_docs["documents"]
    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    
    # Get top_k indices
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    
    chunks = []
    for idx in top_indices:
        if scores[idx] > 0: # Only include if there's a match
            chunks.append({
                "text": corpus[idx],
                "metadata": all_docs["metadatas"][idx],
                "score": float(scores[idx]) # BM25 score is not 0-1
            })
    return chunks


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Tìm kiếm kết hợp (Hybrid Retrieval):
    - Gộp kết quả từ Dense (Ngữ nghĩa) và Sparse (Từ khóa) bằng Reciprocal Rank Fusion (RRF).
    - Giúp hệ thống vừa hiểu được ý nghĩa câu hỏi, vừa bắt được các mã lỗi/từ chuyên ngành chính xác.
    - RRF score được tính dựa trên thứ hạng (rank) của văn bản trong cả 2 danh sách kết quả.
    """
    dense_results = retrieve_dense(query, top_k=top_k * 2)
    sparse_results = retrieve_sparse(query, top_k=top_k * 2)

    # Reciprocal Rank Fusion (RRF)
    rrf_scores = {} # (doc_text, source) -> score
    doc_map = {} # (doc_text, source) -> chunk_dict

    for rank, chunk in enumerate(dense_results):
        key = (chunk["text"], chunk["metadata"]["source"])
        doc_map[key] = chunk
        rrf_scores[key] = rrf_scores.get(key, 0) + dense_weight * (1.0 / (60 + rank))

    for rank, chunk in enumerate(sparse_results):
        key = (chunk["text"], chunk["metadata"]["source"])
        doc_map[key] = chunk
        rrf_scores[key] = rrf_scores.get(key, 0) + sparse_weight * (1.0 / (60 + rank))

    # Sort by RRF score
    sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
    
    hybrid_results = []
    for key in sorted_keys[:top_k]:
        chunk = doc_map[key]
        chunk["score"] = rrf_scores[key]
        hybrid_results.append(chunk)

    return hybrid_results


def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Sắp xếp lại (Reranking):
    - Sử dụng model Cross-Encoder mạnh mẽ hơn để chấm điểm lại top 10 candidates.
    - Model này "nhìn" cả query và chunk cùng lúc để đánh giá mức độ liên quan.
    - Giúp lọc bỏ các chunk "nhiễu" có vector tương đồng nhưng nội dung không thực sự trả lời được câu hỏi.
    """
    if not candidates:
        return []

    from sentence_transformers import CrossEncoder
    
    # Cache model to tránh việc load lại mỗi lần gọi
    if not hasattr(rerank, "model"):
        print("[Rerank] Đang load model Cross-Encoder...")
        rerank.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    pairs = [[query, chunk["text"]] for chunk in candidates]
    scores = rerank.model.predict(pairs)
    
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    
    # Cập nhật score và lọc lấy top_k
    results = []
    for chunk, score in ranked[:top_k]:
        chunk["score"] = float(score)
        results.append(chunk)
        
    return results


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng độ phủ (recall) khi tìm kiếm.
    
    Quy trình:
    1. Gọi LLM để phân tích ý định (intent) của người dùng.
    2. Tùy theo chiến thuật (strategy) để sinh ra các câu truy vấn mới:
       - 'expansion': Thêm đồng nghĩa, tên khác (vd: 'mật khẩu' -> 'password', 'reset').
       - 'decomposition': Tách câu phức thành nhiều câu đơn.
       - 'hyde': Tự viết một câu trả lời mẫu rồi dùng nó để đi tìm tài liệu thật.
    """
    if not strategy or strategy == "none":
        return [query]

    # Cần gọi LLM để xử lý
    from index import call_openai_llm # Hoặc dùng helper call_llm đã có trong file

    if strategy == "expansion":
        prompt = f"""You are an IT Helpdesk expert. Please provide 2-3 alternative phrasings or related search terms in Vietnamese for the following query:
Query: '{query}'
Requirements: Output ONLY a JSON array of strings. Example: ["sentence 1", "sentence 2"]"""
    
    elif strategy == "decomposition":
        prompt = f"""Break down this complex IT Helpdesk query into 2-3 simpler sub-queries in Vietnamese to improve database retrieval:
Query: '{query}'
Requirements: Output ONLY a JSON array of strings. Example: ["query 1", "query 2"]"""
    
    elif strategy == "hyde":
        prompt = f"""Please write a short (2-3 sentences) hypothetical answer in Vietnamese for the following question to be used as a search document:
Question: '{query}'
Hypothetical Answer:"""
        # Với HyDE, prompt trả về text, không phải JSON
        try:
            hyde_doc = call_llm(prompt)
            return [query, hyde_doc] # Trả về cả query gốc và doc giả định
        except:
            return [query]

    else:
        return [query]

    # Xử lý kết quả JSON cho expansion và decomposition
    try:
        import json
        response = call_llm(prompt)
        # Parse mảng JSON từ response
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            new_queries = json.loads(match.group())
            # Luôn giữ lại câu hỏi gốc để đảm bảo an toàn
            return list(set([query] + new_queries))
    except:
        pass

    return [query]


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.

    Format: structured snippets với source, section, score (từ slide).
    Mỗi chunk có số thứ tự [1], [2], ... để model dễ trích dẫn.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")

        # TODO: Tùy chỉnh format nếu muốn (thêm effective_date, department, ...)
        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if score > 0:
            header += f" | score={score:.2f}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xây dựng grounded prompt theo 4 quy tắc từ slide:
    1. Evidence-only: Chỉ trả lời từ retrieved context
    2. Abstain: Thiếu context thì nói không đủ dữ liệu
    3. Citation: Gắn source/section khi có thể
    4. Short, clear, stable: Output ngắn, rõ, nhất quán

    TODO Sprint 2:
    Đây là prompt baseline. Trong Sprint 3, bạn có thể:
    - Thêm hướng dẫn về format output (JSON, bullet points)
    - Thêm ngôn ngữ phản hồi (tiếng Việt vs tiếng Anh)
    - Điều chỉnh tone phù hợp với use case (CS helpdesk, IT support)
    """
    prompt = f"""Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời.

    TODO Sprint 2:
    Chọn một trong hai: OpenAI hoặc Google Gemini.
    """
    provider = os.getenv("LLM_PROVIDER", "openai")

    if provider == "openai":
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("sk-..."):
             return "Lỗi: Chưa cấu hình OPENAI_API_KEY trong file .env"
        
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        return response.choices[0].message.content
    elif provider == "gemini":
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Lỗi: Chưa cấu hình GOOGLE_API_KEY trong file .env"
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
        response = model.generate_content(prompt)
        return response.text
    else:
        return "Lỗi: LLM_PROVIDER không hợp lệ. Chọn 'openai' hoặc 'gemini'."


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    use_transform: bool = False,
    transform_strategy: str = "expansion",
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        verbose: In thêm thông tin debug

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng

    TODO Sprint 2 — Implement pipeline cơ bản:
    1. Chọn retrieval function dựa theo retrieval_mode
    2. Gọi rerank() nếu use_rerank=True
    3. Truncate về top_k_select chunks
    4. Build context block và grounded prompt
    5. Gọi call_llm() để sinh câu trả lời
    6. Trả về kết quả kèm metadata

    TODO Sprint 3 — Thử các variant:
    - Variant A: đổi retrieval_mode="hybrid"
    - Variant B: bật use_rerank=True
    - Variant C: thêm query transformation trước khi retrieve
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "use_transform": use_transform,
        "transform_strategy": transform_strategy,
    }

    # --- Bước 0: Transform Query (Nếu bật) ---
    queries = [query]
    if use_transform:
        if verbose: print(f"[Transform] Đang sử dụng chiến thuật: {transform_strategy}")
        queries = transform_query(query, strategy=transform_strategy)
        if verbose: print(f"[Transform] Các câu hỏi mới: {queries}")

    # --- Bước 1: Tìm kiếm (Retrieve) ---
    all_candidates = []
    for q in queries:
        if retrieval_mode == "dense":
            all_candidates.extend(retrieve_dense(q, top_k=top_k_search))
        elif retrieval_mode == "sparse":
            all_candidates.extend(retrieve_sparse(q, top_k=top_k_search))
        elif retrieval_mode == "hybrid":
            all_candidates.extend(retrieve_hybrid(q, top_k=top_k_search))
    
    # Gộp và khử trùng lặp candidates
    unique_candidates = {}
    for cand in all_candidates:
        key = (cand["text"], cand["metadata"].get("source"))
        # Giữ lại candidate có score cao nhất nếu trùng lặp
        if key not in unique_candidates or cand.get("score", 0) > unique_candidates[key].get("score", 0):
            unique_candidates[key] = cand
    
    candidates = sorted(unique_candidates.values(), key=lambda x: x.get("score", 0), reverse=True)
    candidates = candidates[:top_k_search * 2] # Giữ lại danh sách đủ rộng để rerank

    if verbose:
        print(f"\n[RAG] Query gốc: {query}")
        print(f"[RAG] Đã tìm thấy {len(candidates)} đoạn văn bản sau khi gộp {len(queries)} truy vấn.")

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract sources ---
    sources = list({
        c["metadata"].get("source", "unknown")
        for c in candidates
    })

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.

    TODO Sprint 3:
    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "hybrid"]  # Thêm "sparse" sau khi implement

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError as e:
            print(f"Chưa implement: {e}")
        except Exception as e:
            print(f"Lỗi: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Test queries từ data/test_questions.json
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",  # Query không có trong docs → kiểm tra abstain
    ]

    print("\n--- Sprint 2: Test Baseline (Dense) ---")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = rag_answer(query, retrieval_mode="dense", verbose=True)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError:
            print("Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước.")
        except Exception as e:
            print(f"Lỗi: {e}")

    # Sprint 3: So sánh strategies
    print("\n--- Sprint 3: So sánh strategies ---")
    compare_retrieval_strategies("SLA xử lý ticket P1 là bao lâu?")
    compare_retrieval_strategies("ERR-403-AUTH")

    print("\n\nViệc cần làm Sprint 2:")
    print("  1. Implement retrieve_dense() — query ChromaDB")
    print("  2. Implement call_llm() — gọi OpenAI hoặc Gemini")
    print("  3. Chạy rag_answer() với 3+ test queries")
    print("  4. Verify: output có citation không? Câu không có docs → abstain không?")

    print("\nViệc cần làm Sprint 3:")
    print("  1. Chọn 1 trong 3 variants: hybrid, rerank, hoặc query transformation")
    print("  2. Implement variant đó")
    print("  3. Chạy compare_retrieval_strategies() để thấy sự khác biệt")
    print("  4. Ghi lý do chọn biến đó vào docs/tuning-log.md")
