# System Architecture — Lab Day 09

**Nhóm:** Nhóm C401 - A3
**Ngày:** 14/04/2026
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker Graph (StateGraph Orchestration Pattern)
**Lý do chọn pattern này (thay vì single agent):**
- **Sự phân tách trách nhiệm (Separation of Concerns):** Mỗi agent (worker) đảm nhận một tác vụ chuyên biệt, giúp tránh việc một agent bị quá tải prompt và dễ bị ảo giác (hallucination).
- **Khả năng quan sát (Observability):** Chúng ta dễ dàng theo dõi đường đi của tin nhắn, lịch sử, độ trễ và các tool đã gọi nhờ có đối tượng `AgentState` xuyên suốt vòng đời.
- **Dễ dàng mở rộng, gỡ lỗi (Scalability & Debugging):** Có thể nâng cấp LLM hoặc logic cho từng worker một cách hoàn toàn độc lập (vd: đổi model cho Synthesis mà không ảnh hưởng Retrieval). Các trường hợp rủi ro cao (như mã lỗi `err-`) dễ dàng được nắn dòng để chờ duyệt thủ công.

---

## 2. Sơ đồ Pipeline

**Sơ đồ thực tế của nhóm:**

```text
                      [User Request]
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │                      Supervisor                        │
 │         (Xử lý Routing, Risk, Needs_tool flags)        │
 └───────────────────────────┬────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            │         Route Decision          │
            └──────┬─────────┬─────────┬──────┘
                   │         │         │
    [human_review] │         │         │ [retrieval_worker]
                   ▼         │         ▼
      ┌────────────────┐     │  ┌──────────────────────┐
      │  Human Review  │     │  │   Retrieval Worker   │
      │    (Pause)     │     │  │ (ChromaDB / Vector)  │
      └───────┬────────┘     │  └──────────┬───────────┘
              │(Approved)    │             │ (Context)
              │              │             │
              ▼              ▼             │
[policy_tool_worker]  ┌──────────────┐     │
--------------------> │ Policy Tool  │<────┘
                      │    Worker    │
                      └──────┬───────┘
                             │ (Checks & calls MCP)
                             ▼
                     [ MCP Server Tools ]
                (search_kb, get_ticket_info)
                             │
                             ▼
                    ┌──────────────────┐
                    │ Synthesis Worker │
                    │ (LLM + Citation) │
                    └────────┬─────────┘
                             │
                             ▼
                       [Final Output]
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích intent của Task, phân loại và chọn Route/Luồng thích hợp; quản lý state chung. |
| **Input** | `state["task"]` (Câu hỏi từ người dùng) |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool` |
| **Routing logic** | String/Keyword matching (thay vì LLM để tiết kiệm chi phí/latency):<br>1. "err-" -> `human_review`<br>2. Policy keywords ("refund, flash sale, cấp quyền") -> `policy_tool_worker`<br>3. System/SLA keywords ("p1, sla, incident") -> `retrieval_worker` |
| **HITL condition** | Khi hệ thống đánh dấu `risk_high = True` (mã lỗi lạ không xác định). |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Truy vấn CSDL cơ sở (ChromaDB) để trích xuất các chunks tài liệu liên quan đến Task. |
| **Embedding model** | `all-MiniLM-L6-v2` (thuộc thư viện `sentence-transformers`) |
| **Top-k** | 3 (Mặc định) |
| **Stateless?** | Yes. (Worker này có thể bị tháo rời để test độc lập mà không cần môi trường xung quanh). |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Đánh giá sự tuân thủ quy chế kiểm duyệt (SLA, Refund policy) và dùng MCP gọi API nội bộ khi thiếu thông tin. |
| **MCP tools gọi** | `search_kb`, `check_access_permission`, `get_ticket_info`, `create_ticket`. |
| **Exception cases xử lý** | Đơn hàng Flash Sale (ko hoàn tiền), Sản phẩm Digital (ko hoàn tiền), Sản phẩm đã kích hoạt, Đơn trước 01/02/2026. |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | Trình đa mô hình khả dụng: `gpt-4o-mini` hoặc `gemini-1.5-flash` |
| **Temperature** | `0.1` (Sử dụng low temperature để tạo tính Grounded, giảm thiếu tối đa ảo giác) |
| **Grounding strategy** | Chỉ cho phép trả lời các nội dung được nạp qua Context chunks. Bắt buộc có Citation định dạng dạng `[1] Nguồn: ...` |
| **Abstain condition** | "Không đủ thông tin trong tài liệu nội bộ" nếu context chunks bị rỗng. Trả lại confidence cực thấp (`0.1 - 0.3`). |

### MCP Server (`mcp_server.py`)

Thành phần cung cấp các Capability bên ngoài qua kiến trúc Mock Model Context Protocol.

| Tool | Input Schema | Output Schema |
|------|-------|--------|
| `search_kb` | `query` (str), `top_k` (int) | `chunks` (list), `sources` (list), `total_found` (int) |
| `get_ticket_info` | `ticket_id` (str) | `ticket_id`, `priority`, `status`, `assignee`, v.v... |
| `check_access_permission` | `access_level` (int), `requester_role` (str), `is_emergency` (bool) | `can_grant`, `required_approvers`, `emergency_override` |
| `create_ticket` | `priority` (str), `title` (str), `description` (str) | `ticket_id`, `url`, `created_at` (Log thời điểm gọi tạo ticket) |

---

## 4. Shared State Schema

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| `task` | str | Câu hỏi đầu vào của người dùng | user ghi, supervisor & mọi worker đều đọc |
| `supervisor_route` | str | Xác định Worker tiếp theo sẽ gọi | supervisor ghi, graph đọc để điều hướng luồng |
| `route_reason` | str | Lý do diễn giải cho việc Route. | supervisor ghi, trace (hitl) đọc |
| `needs_tool` | bool | Quyết định xem có nên cấp quyền gọi Tool / Database ẩn không | supervisor ghi, policy_tool đọc |
| `risk_high` | bool | Có rủi ro không (khi gặp error code lạ) | supervisor ghi |
| `retrieved_chunks` | list | Bằng chứng / Context tham khảo | retrieval ghi, policy & synthesis đọc |
| `policy_result` | dict | Bảng kết quả báo cáo compliance | policy_tool ghi, synthesis đọc |
| `mcp_tools_used` | list | Tập Tool calls bên ngoài đã thực hiện | policy_tool ghi, eval trace đọc |
| `final_answer` | str | Câu trả lời cuối cho user | synthesis ghi, user đọc |
| `confidence` | float | Đội tin cậy (Dựa trên số luợng chunks + exceptions) | synthesis ghi |
| `history` | list | Dòng thời gian Log di chuyển State qua Graph | Tất cả các Nodes chèn thêm, eval báo cáo đọc |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| **Debug khi sai** | Khó — không rõ lỗi xuất phát ở khâu retrieval, phân tích luật, hay sinh text. | Rất Dễ — test từng cụm worker độc lập bằng JSON log (`worker_io_log`). |
| **Thêm API mới** | Phải nhồi thêm vào prompt trung tâm, dễ gây loãng và Hallucination hệ thống. | Thêm trực tiếp 1 hàm MCP tool và cấp quyền cho đúng Policy Worker xử lý. |
| **Routing visibility**| Không có định tuyến, phải hỏi 1 con duy nhất. | Rõ ràng với `route_reason` được log trên Tracker Graph. |
| **Bảo mật & Hitl** | Nếu Agent gặp rủi ro, đôi lúc nó vẫn trả lời liều. | Trạng thái rủi ro tách bạch (Có luồng Human in the Loop chặn lại khi gặp Risk cao). |

**Quan sát từ thực tiễn khi làm phân tán ở nhóm:**
Hệ thống cho phép các thành viên (6 roles) phát triển song song mà không dẫm chân lên nhau. Phase 4 phát triển Policy mà không cần phải chờ đợi Phase 2 code xong Retrieval vì Context inputs đều có thể linh động mock tĩnh thông qua test object ở file độc lập.

---

## 6. Giới hạn và điểm cần cải tiến

1. **Routing quá cứng nhắc:** Cơ chế String Matching (Rule-based) bằng mảng arrays `policy_keywords` nhanh về mặt tốc độ latency nhưng sẽ lỗi nếu người dùng không dùng từ khoá đúng chính tả / đồng nghĩa. Cải tiến tương lai: Semantic Routing bằng 1 LLM con nhúng (Embedding router) cho Supervisor.
2. **Evaluation Metrics chưa tối ưu:** Mức độ `confidence` mới được ước lượng dựa trên số lượng penalty điểm trung bình của câu (tại `synthesis.py`), chưa sát với ngữ nghĩa thực thế. Cải tiến tương lai: Áp dụng phương pháp LLM-as-a-judge ở cuối chu trình đánh giá.
3. **Mô hình MCP tĩnh:** Server MCP đang dùng các biến dict tĩnh. Cải tiến tương lai: Bọc MCP qua Express Server / FastAPI để gọi bằng cơ chế SSE (Server-Sent Events) nhằm tuân thủ tiêu chuẩn đa hệ thống.
