import sys
import os
from rag_answer import rag_answer

# Hỗ trợ in tiếng Việt trên console Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("="*60)
    print("🤖 HỆ THỐNG HỖ TRỢ NỘI BỘ (AI CHATBOT)")
    print("="*60)
    print("Gõ 'exit' hoặc 'quit' để thoát.\n")

    while True:
        try:
            # Dùng input trực tiếp, Windows cần lưu ý mã hóa nếu lỗi fonts
            query = input("💬 Bạn hỏi: ").strip()
            
            if query.lower() in ['exit', 'quit', 'thoát']:
                print("Tạm biệt!")
                break
            
            if not query:
                continue

            print("🔍 Đang tìm câu trả lời...")
            
            # Sử dụng retrieval_mode="hybrid" để có độ chính xác cao nhất
            result = rag_answer(query, retrieval_mode="hybrid", verbose=False)

            print(f"\n✨ TRẢ LỜI:")
            print(f"{result['answer']}")
            
            print(f"\n📚 NGUỒN TRÍCH DẪN:")
            if result['sources']:
                for source in result['sources']:
                    # Lấy tên file cho gọn
                    source_name = os.path.basename(source)
                    print(f"  - {source_name}")
            else:
                print("  (Không tìm thấy nguồn cụ thể)")
            
            print("-" * 60)
            print()

        except KeyboardInterrupt:
            print("\nĐã dừng chương trình.")
            break
        except Exception as e:
            print(f"❌ Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    main()
