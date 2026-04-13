import os
from rag_answer import rag_answer

def start_chat():
    print("="*60)
    print("🤖 IT HELPDESK RAG CHATBOT (Nhập 'exit' để thoát)")
    print("="*60)
    
    # Cấu hình mặc định: Hybrid + Rerank để có chất lượng tốt nhất
    config = {
        "retrieval_mode": "hybrid",
        "use_rerank": True,
        "verbose": False
    }

    while True:
        query = input("\n👤 Bạn: ").strip()
        
        if query.lower() in ["exit", "quit", "thoát", "bye"]:
            print("Cảm ơn bạn đã sử dụng chatbot. Tạm biệt!")
            break
            
        if not query:
            continue
            
        print("⏳ Đang tìm câu trả lời...")
        try:
            res = rag_answer(query, **config)
            
            print(f"\n🤖 AI: {res['answer']}")
            if res['sources']:
                # Lấy tên file ngắn gọn thay vì đường dẫn tuyệt đối
                source_names = list(set([s.split("/")[-1] for s in res['sources']]))
                print(f"📍 Nguồn: {', '.join(source_names)}")
            else:
                print("📍 Nguồn: Không tìm thấy tài liệu phù hợp.")
                
        except Exception as e:
            print(f"❌ Có lỗi xảy ra: {e}")
        
        print("-" * 30)

if __name__ == "__main__":
    start_chat()
