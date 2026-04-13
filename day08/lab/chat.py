import os
from rag_answer import rag_answer

def print_settings(config):
    print("\n⚙️  CẤU HÌNH HIỆN TẠI:")
    print(f"  1. Retrieval Mode: {config['retrieval_mode']}")
    print(f"  2. Rerank: {'BẬT ✅' if config['use_rerank'] else 'TẮT ❌'}")
    print(f"  3. Transform Query: {'BẬT ✅' if config['use_transform'] else 'TẮT ❌'}")
    if config['use_transform']:
        print(f"     └─ Strategy: {config['transform_strategy']}")
    print("-" * 30)

def start_chat():
    print("="*60)
    print("🤖 IT HELPDESK RAG CHATBOT")
    print("  - Gõ '/config' để thay đổi cấu hình")
    print("  - Gõ 'exit' để thoát")
    print("="*60)
    
    # Cấu hình mặc định
    config = {
        "retrieval_mode": "hybrid",
        "use_rerank": True,
        "use_transform": False,
        "transform_strategy": "expansion",
        "verbose": True # Bật verbose để bạn thấy quá trình transform
    }

    print_settings(config)

    while True:
        query = input("\n👤 Bạn: ").strip()
        
        if query.lower() in ["exit", "quit", "thoát"]:
            print("Cảm ơn bạn đã sử dụng chatbot. Tạm biệt!")
            break

        if query.lower() == "/config":
            print("\n--- THAY ĐỔI CẤU HÌNH ---")
            print("1. Retrieval Mode (dense/sparse/hybrid)")
            print("2. Toggle Rerank")
            print("3. Toggle Transform Query")
            print("4. Transform Strategy (expansion/decomposition/hyde)")
            print("5. Quay lại chat")
            
            choice = input("Chọn mục (1-5): ").strip()
            if choice == "1":
                mode = input("Nhập mode (dense/sparse/hybrid): ").strip().lower()
                if mode in ["dense", "sparse", "hybrid"]: config["retrieval_mode"] = mode
            elif choice == "2":
                config["use_rerank"] = not config["use_rerank"]
            elif choice == "3":
                config["use_transform"] = not config["use_transform"]
            elif choice == "4":
                strat = input("Nhập strategy (expansion/decomposition/hyde): ").strip().lower()
                if strat in ["expansion", "decomposition", "hyde"]: config["transform_strategy"] = strat
            
            print_settings(config)
            continue
            
        if not query:
            continue
            
        print("⏳ Đang xử lý...")
        try:
            res = rag_answer(query, **config)
            
            print(f"\n🤖 AI: {res['answer']}")
            if res['sources']:
                source_names = list(set([s.split("/")[-1] for s in res['sources']]))
                print(f"📍 Nguồn: {', '.join(source_names)}")
            else:
                print("📍 Nguồn: Không tìm thấy tài liệu phù hợp.")
                
        except Exception as e:
            print(f"❌ Có lỗi xảy ra: {e}")
        
        print("-" * 30)

if __name__ == "__main__":
    start_chat()
