# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Văn Bách  
**Vai trò trong nhóm:** Worker Owner (Policy & Compliance)  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ (Bản thảo chi tiết)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án Lab 9 về hệ thống điều phối đa nhân sự (Multi-Agent Orchestration), tôi trực tiếp chịu trách nhiệm xây dựng thành phần **Policy & Compliance Worker**. Đây là một nút quan trọng trong đồ thị (Graph) làm nhiệm vụ kiểm soát các quy chế của công ty liên quan đến bảo mật và chính sách khách hàng.

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/policy_tool.py`
- Functions tôi implement: `run(state)`, `analyze_policy(task, chunks)`, `call_llm_policy_analysis(...)`, `_call_mcp_tool(...)`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Công việc của tôi đóng vai trò là "người gác cổng" sau khi Supervisor (Phase 1) phân loại yêu cầu. Tôi nhận dữ liệu thô từ Retrieval Worker (Phase 2), sau đó sử dụng các công cụ từ MCP Server (Phase 3) để tra cứu bổ sung thông tin như trạng thái Jira Ticket hoặc mức độ ưu tiên. Kết quả phân tích của tôi (`policy_result`) là đầu vào bắt buộc để Synthesis Worker (Phase 5) tổng hợp câu trả lời cuối cùng cho người dùng một cách chính xác và tuân thủ quy định.

**Bằng chứng:**
File `workers/policy_tool.py` chứa toàn bộ logic xử lý chuyển đổi từ rule-base sang LLM-based mà tôi đã thực hiện trong các lần refactor.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Chuyển đổi hoàn toàn cơ chế kiểm tra chính sách từ sử dụng **Regex/Rule-based** sang **LLM-based Analysis (sử dụng GPT-4o-mini)**.

**Lý do:**
Ban đầu, tôi định nghĩa các chính sách hoàn tiền bằng các câu lệnh `if/else` đơn giản dựa trên từ khóa như "flash sale" hay "license". Tuy nhiên, tôi nhận thấy các câu hỏi của người dùng thường mang tính ngữ cảnh cao (ví dụ: "Sản phẩm lỗi nhưng mua từ đợt Flash Sale"). Logic cứng nhắc sẽ rất khó để bắt được các sắc thái này hoặc xử lý các ngoại lệ phức tạp về thời hạn (temporal scoping).
Tôi quyết định sử dụng LLM với một System Prompt được thiết kế chuyên biệt để đóng vai chuyên gia pháp chế. Quyết định này giúp Worker không chỉ trả về đúng/sai mà còn đưa ra được lời giải thích (`explanation`) bằng ngôn ngữ tự nhiên, giúp Synthesis Worker làm việc nhàn hơn và câu trả lời cuối cùng có tính thuyết phục cao hơn.

**Trade-off đã chấp nhận:**
Sử dụng LLM làm tăng độ trễ (latency) của worker (~1.5s so với gần như 0ms của rule-based) và tốn chi phí token. Tuy nhiên, với các tác vụ liên quan đến Complience (tuân thủ), tôi ưu tiên **độ chính xác và khả năng diễn giải** hơn là tốc độ thuần túy.

**Bằng chứng từ code:**
```python
# System prompt tôi thiết kế để AI bắt các ngoại lệ chính xác
system_prompt = """You are an internal Policy Analyst. 
...
EXCEPTIONS TO CHECK:
1. Flash Sale: Flash Sale orders are NOT eligible for refunds.
2. Digital Products/Services: License keys, subscriptions, and activated software...
...
"""
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Tên biến không xác định (`NameError: name 'task_lower' is not defined`) khi thực hiện chế độ Fallback.

**Symptom:**
Trong quá trình kiểm thử độc lập (Standalone test), khi tôi giả lập tình huống LLM API bị lỗi (để test cơ chế dự phòng), Pipeline bị crash hoàn toàn với lỗi `NameError`.

**Root cause:**
Khi refactor code, tôi đã di chuyển phần tiền xử lý chuỗi (`task.lower()`) vào sâu trong logic của LLM. Tuy nhiên, hàm `analyze_policy` vẫn giữ lại các đoạn code rule-based ở phía cuối làm fallback. Khi LLM thất bại, luồng code nhảy xuống fallback và cố gắng truy cập vào `task_lower` - biến mà lúc đó chưa được khởi tạo ở phạm vi bên ngoài.

**Cách sửa:**
Tôi đã đưa các biến tiền xử lý cơ bản lên đầu hàm `analyze_policy`, đảm bảo chúng luôn khả dụng cho cả luồng LLM lẫn luồng dự phòng (fallback).

**Bằng chứng sau khi sửa:**
```python
def analyze_policy(task: str, chunks: list) -> dict:
    # Đưa lên đầu để tránh NameError cho fallback
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks]).lower()
    ...
```
Kết quả test sau đó: `▶ Task: Khách hàng Flash Sale... policy_applies: False. Analyzed via rule-based fallback (LLM failed).` -> Chạy thành công.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã hoàn thiện việc tích hợp **Model Context Protocol (MCP)** một cách tự động. Worker của tôi không chỉ ngồi đợi context mà còn chủ động gọi `check_access_permission` hoặc `get_ticket_info` dựa trên phân tích từ khóa của task, giúp tăng cường đáng kể lượng thông tin đầu vào mà Supervisor không cần phải can thiệp quá sâu.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Ban đầu tôi quên mất việc giới hạn ngôn ngữ trả về cho LLM. AI đã trả về giải thích bằng tiếng Anh cho các tài liệu nội bộ tiếng Việt, làm mất tính đồng nhất của hệ thống. Tôi đã phải sửa lại Prompt để ràng buộc hướng dẫn "Respond in the same language as the context".

**Nhóm phụ thuộc vào tôi ở đâu?**
Toàn bộ logic xử lý Ticket P1 và các yêu cầu hoàn tiền nhạy cảm sẽ bị sai lệch nếu Policy Worker của tôi không hoạt động. Nếu thiếu phần này, hệ thống sẽ chỉ là một RAG thông thường, không có tính "Compliance".

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào `mcp_server.py` của Phase 3. Nếu interface `dispatch_tool` thay đổi cấu trúc Input/Output, code của tôi sẽ bị lỗi kết nối ngay lập tức.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ tập trung cải tiến cơ chế **Self-Correction**. Cụ thể, tôi sẽ thêm một bước kiểm tra chéo: nếu LLM tìm thấy ngoại lệ, nó phải trích dẫn chính xác dòng nào trong tài liệu nội bộ chứa quy định đó (ví dụ: "Theo điều 3.1 file policy_refund_v4.txt"). Hiện tại, AI của tôi mới chỉ dừng lại ở việc nêu tên file chung chung. Điều này sẽ giúp báo cáo của Phase 6 (Trace) có độ tin cậy tuyệt đối.

---
*Lưu file này với tên: `reports/individual/nguyen_van_bach.md`*  
