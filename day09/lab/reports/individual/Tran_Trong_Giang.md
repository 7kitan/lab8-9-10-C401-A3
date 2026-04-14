# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Trọng Giang  
**Vai trò trong nhóm:** MCP Owner  
**Ngày nộp:** 2026-04-14  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `mcp_server.py`
- Functions tôi implement: `tool_search_kb`, `tool_get_ticket_info`, `tool_check_access_permission`, `tool_create_ticket`, `dispatch_tool`, `dispatch_tool_with_trace`, `list_tools`

Trong Lab Day 09, tôi chịu trách nhiệm xây dựng toàn bộ module **MCP Server API Interface**. Cụ thể, tôi đã hiện thực 4 công cụ theo chuẩn Model Context Protocol: `search_kb` (tìm kiếm Knowledge Base), `get_ticket_info` (tra cứu ticket), `check_access_permission` (kiểm tra quyền truy cập), và `create_ticket` (tạo ticket mới). Ngoài ra, tôi xây dựng lớp Dispatcher (`dispatch_tool`) để các Worker gọi công cụ qua tên và payload, cùng wrapper `dispatch_tool_with_trace` cung cấp metadata cho hệ thống Trace.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Module `mcp_server.py` của tôi là cầu nối giữa Knowledge Base và các Worker. Phase 4 (Policy Worker) gọi `dispatch_tool_with_trace("search_kb", ...)` hoặc `dispatch_tool_with_trace("get_ticket_info", ...)` để lấy dữ liệu phục vụ kiểm tra policy. Phase 6 (Trace Owner) sử dụng trường `mcp_tools_used` do wrapper tôi viết tạo ra để ghi vào trace file.

**Bằng chứng:** File `mcp_server.py` chứa comment `# Giang - MCP Owner` và toàn bộ logic 4 tools + dispatcher.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Hiện thực cơ chế **Keyword-search Fallback với Relevance Scoring** trong công cụ `search_kb`, thay vì chỉ phụ thuộc hoàn toàn vào ChromaDB.

**Các lựa chọn thay thế:**
1. Chỉ dùng ChromaDB — đơn giản nhưng pipeline crash nếu ChromaDB chưa setup.
2. Trả về mock data cứng — pipeline chạy nhưng câu trả lời luôn sai.
3. **Keyword fallback + relevance scoring** — đọc trực tiếp `data/docs/*.txt`, chia chunk theo đoạn, tính điểm dựa trên tỷ lệ keywords matched.

**Tại sao tôi chọn cách 3:** Trong môi trường làm việc nhóm, việc cài đặt ChromaDB có thể không đồng bộ. Cách 3 giúp hệ thống luôn ở trạng thái "Always Runnable" và trả về kết quả có ý nghĩa ngay cả khi chưa có Vector Database.

**Trade-off đã chấp nhận:** Keyword search kém chính xác hơn semantic search (ChromaDB). Tuy nhiên, trong phạm vi 5 tài liệu nội bộ của lab, keyword matching đủ tốt để tìm đúng tài liệu.

**Bằng chứng từ trace/code:**

```python
# mcp_server.py - search_kb fallback logic (line 157-182)
keywords = [kw for kw in query.lower().split() if len(kw) > 1]
matched = sum(1 for kw in keywords if kw in section_lower)
score = round(matched / max(len(keywords), 1), 2)
```

Test kết quả: Query "SLA P1 escalation" → trả về đúng `sla_p1_2026.txt` (score 1.0). Query "refund policy flash sale" → trả về đúng `policy_refund_v4.txt`.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Keyword fallback trả về tài liệu không liên quan do thuật toán scoring thiếu chính xác.

**Symptom:** Khi chạy `dispatch_tool("search_kb", {"query": "SLA P1 escalation"})`, kết quả trả về là `it_helpdesk_faq.txt` và `access_control_sop.txt` thay vì `sla_p1_2026.txt`. Tương tự, query "refund policy flash sale" trả về `hr_leave_policy.txt` thay vì `policy_refund_v4.txt`. Pipeline trả lời sai hoàn toàn vì dùng ngữ cảnh từ tài liệu không liên quan.

**Root cause:** Phiên bản đầu gán score cứng `0.8` cho mọi chunk chỉ cần chứa 1 keyword bất kỳ. Ví dụ, từ "escalation" xuất hiện trong cả `access_control_sop.txt` lẫn `sla_p1_2026.txt`, nhưng cả hai đều nhận cùng score → thứ tự trả về phụ thuộc vào thứ tự đọc file, không phải mức độ liên quan.

**Cách sửa:** Thay đổi thuật toán scoring từ flat score sang **tỷ lệ keywords matched**:
- Đếm số keywords trong query khớp với mỗi chunk
- Score = `matched_count / total_keywords`
- Lọc bỏ keywords quá ngắn (≤1 ký tự) để tránh noise

**Bằng chứng trước/sau:**
- **Trước:** query "SLA P1 escalation" → sources: `['it_helpdesk_faq.txt', 'access_control_sop.txt']` ❌
- **Sau:** query "SLA P1 escalation" → sources: `['sla_p1_2026.txt']` ✅ (score 1.0 vì 3/3 keywords matched)

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Xây dựng module có tính module hóa cao, dễ test độc lập. Viết bộ test 75 test cases bao phủ toàn bộ tools, edge cases, contract compliance và keyword fallback quality. Tất cả 75/75 cases đều PASS.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Chưa implement được MCP Server dạng HTTP thật sự (chỉ dừng ở mức Standard Mock Class) do ưu tiên tính ổn định cho toàn nhóm. Mất thời gian debug lỗi encoding trên Windows.

**Nhóm phụ thuộc vào tôi ở đâu?**

Phase 4 (Policy Worker) cần `dispatch_tool` / `dispatch_tool_with_trace` từ module tôi để gọi MCP tools. Nếu module này chưa xong, Policy Worker không thể kiểm tra policy qua external tools.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi cần hàm `retrieve_dense()` từ Phase 2 (Retrieval Worker) để `search_kb` dùng ChromaDB thay vì fallback. Tuy nhiên, nhờ có cơ chế fallback, tôi có thể hoạt động độc lập.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ implement **FastAPI-based MCP Server** thật sự (bonus +2 điểm) vì kết quả test cho thấy mock class hoạt động ổn định. Cụ thể, tôi sẽ expose `dispatch_tool` qua HTTP endpoint `POST /tools/call` để Policy Worker gọi qua network thay vì import trực tiếp. Điều này giúp hệ thống thực sự tách biệt (decoupled), mô phỏng đúng cách MCP protocol hoạt động trong production, và cho phép các Worker chạy ở các process khác nhau.
