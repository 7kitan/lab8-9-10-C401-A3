import json
from pathlib import Path
from rag_answer import rag_answer

def run_stress_test():
    test_path = Path("data/stress_test_questions.json")
    if not test_path.exists():
        print(f"Lỗi: Không tìm thấy file {test_path}")
        return

    with open(test_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print("="*80)
    print("RAG STRESS TEST - KIỂM TRA CHẤT LƯỢNG EDGE CASES")
    print("="*80)

    results = []
    
    # Sử dụng cấu hình mạnh nhất: Hybrid + Rerank
    config = {
        "retrieval_mode": "hybrid",
        "use_rerank": True,
        "verbose": False
    }

    for item in questions:
        print(f"\n[{item['id']}] Category: {item['category']}")
        print(f"Question: {item['question']}")
        
        # Chạy pipeline
        res = rag_answer(item['question'], **config)
        
        print(f"Answer: {res['answer'][:300]}...")
        print(f"Expected Behavior: {item['expected_behavior']}")
        print(f"Sources: {res['sources']}")
        
        # Manual check placeholder
        print("-" * 40)
        
        results.append({
            "id": item['id'],
            "question": item['question'],
            "answer": res['answer'],
            "expected_behavior": item['expected_behavior'],
            "sources": res['sources']
        })

    # Lưu kết quả stress test
    output_path = Path("results/stress_test_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nTest hoàn tất. Kết quả chi tiết đã lưu tại: {output_path}")

if __name__ == "__main__":
    run_stress_test()
