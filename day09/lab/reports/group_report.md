# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Nhóm C401 - A3

**Thành viên:**

| Tên | Vai trò | Email |
|-----|---------|-------|
| Nguyễn Tuấn Kiệt | Worker Owner | <kiet.swe@gmail.com> |
| Nguyễn Văn Bách | Worker Owner | vanbachpk1@gmail.com |
| | | |
| Nguyễn Duy Hưng | Trace & Docs Owner | <hungngduy2003@gmail.com> |

**Ngày nộp:** 14/04/2026

**Repo:** <https://github.com/7kitan/lab8-9-10-C401-A3.git>

**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
>
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn hệ thống nhóm: bao nhiêu workers, routing logic hoạt động thế nào,
> MCP tools nào được tích hợp. Dùng kết quả từ `docs/system_architecture.md`.

**Hệ thống tổng quan:** Nhóm đã xây dựng hệ thống theo mô hình **Supervisor-Worker Graph (StateGraph Orchestration Pattern)**. Hệ thống bao gồm 3 worker chuyên biệt: Retrieval (truy xuất), Policy Tool (kiểm duyệt) và Synthesis (tổng hợp).

**Routing logic cốt lõi:** Supervisor sử dụng phương pháp **Keyword Matching** (SLA, Refund, Access, v.v.) để phân loại yêu cầu nhanh chóng vào các worker đích. Điểm đặc biệt là cơ chế phát hiện mã lỗi lạ (`err-`) để tự động gắn cờ `risk_high=true`, chuyển yêu cầu sang luồng Human Review.

**MCP tools đã tích hợp:**

- `search_kb`: Công cụ tìm kiếm Knowledge Base với cơ chế **Keyword Fallback** (cho phép chạy ngay cả khi ChromaDB chưa sẵn sàng).
- `get_ticket_info`: Truy vấn chi tiết Ticket P1.
- `check_access_permission`: Kiểm định quyền hạn truy cập hệ thống theo roles.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** Sử dụng mô hình **Hybrid Routing** (Kết hợp Keyword-based Routing và LLM-based Policy Analysis).

**Bối cảnh vấn đề:** Nhóm cần giải quyết "nỗi đau" về độ trễ (Latency) của Agentic systems. Nếu sử dụng LLM cho mọi bước chuyển hướng, hệ thống sẽ mất 2-3s chỉ để biết khách hàng muốn gì.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Full LLM Orchestration | Hiểu ngữ cảnh cực tốt, linh hoạt | Độ trễ cao (~3s), tốn chi phí, dễ bị ảo giác Routing |
| Pure Keyword/Rule | Phản hồi tức thì (0ms), giá rẻ | Không xử lý được các từ đồng nghĩa hoặc ngữ cảnh phức tạp |

**Phương án đã chọn và lý do:** Nhóm chọn **Hybrid approach**. Keyword Routing được dùng cho Supervisor (tại `graph.py`) để đạt tính tất định (Deterministic) và độ trễ 0ms. Tuy nhiên, nhóm dùng **LLM (GPT-4o-mini)** cho Policy Worker để thực hiện phân tích tầng sâu các ngoại lệ chính sách (như Flash Sale hay License activated). Điều này giúp hệ thống vừa "Nhanh" ở cửa ngõ, vừa "Thông minh" ở bước ra quyết định nghiệp vụ.

**Bằng chứng từ trace/code:**
Trong file `graph.py`, Supervisor route chính xác task "CS Refund" vào Policy Worker dựa trên keywords, trong khi trace ghi nhận Policy Worker gọi LLM để giải thích tại sao đơn hàng Flash Sale không được hoàn tiền.

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
>
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** 96 / 96

**Câu pipeline xử lý tốt nhất:**

- ID: **gq09** — Lý do tốt: Đây là câu hỏi multi-hop phức tạp yêu cầu cả thông tin P1 SLA và cấp quyền truy cập. Supervisor đã nhận diện đúng tính chất rủi ro khẩn cấp và route chính xác qua 2 worker (Policy -> Retrieval) để lấy đủ bằng chứng.

**Câu pipeline fail hoặc partial:**

- ID: **None** — Hiện tại hệ thống trả lời đúng hướng (routing) cho toàn bộ 10 câu hỏi trong tập chấm điểm chính thức.

**Câu gq07 (abstain):** Nhóm đã thiết kế Synthesis worker để nhận diện khi dữ liệu truy xuất không đề cập đến "phạt tài chính" và trả về thông báo "Không tìm thấy thông tin cụ thể" thay vì bịa ra một con số phạt ngẫu nhiên.

**Câu gq09 (multi-hop khó nhất):** Trace ghi nhận Supervisor route vào `policy_tool_worker`, sau đó luồng đi tiếp qua `retrieval_worker`, đảm bảo quy trình kiểm soát quyền được thực hiện trước khi lấy thông tin kỹ thuật.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):** Độ chính xác cho các câu hỏi phức tạp (multi-hop) tăng từ 40% (Day 08) lên 100% (Day 09) nhờ khả năng phân rã nhiệm vụ cho từng Worker chuyên biệt.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:** Khả năng **Observability**. Chúng ta không còn phải đoán LLM đang nghĩ gì, mà nhìn thấy rõ ràng từng bước di chuyển của `AgentState` qua thuộc tính `history`.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:** Đối với các câu hỏi đơn giản (như "Giờ làm việc của văn phòng?"), việc đi qua Supervisor và Graph Orchestration tạo ra một bước overhead nhỏ không cần thiết so với việc dùng Simple RAG.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nguyễn Tuấn Kiệt | `synthesis.py`, worker testing script | 2 |
| Nguyễn Văn Bách | policy_tool.py | 2 |
| | | |
| Nguyễn Duy Hưng | eval_trace.py, 2 doc templates: routing_decisions & single_vs_multi_comparison, group_report | 4 |

**Điều nhóm làm tốt:** Việc thống nhất **AgentState schema** và **YAML Contracts** ngay từ Sprint 1 là "chìa khóa" giúp cả team phát triển song song. MCP Owner có thể test tool, Worker Owner có thể viết logic phân tích mà không cần đợi Supervisor hoàn thiện Graph.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:** Team gặp khó khăn trong việc đồng bộ môi trường (Virtual Env) và lỗi **Unicode Encode** trên môi trường Windows, dẫn đến việc tích hợp Trace bị chậm hơn dự kiến 30 phút.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?** Nhóm sẽ dành nhiều thời gian hơn để viết Unit Test cho từng Module MCP trước khi nạp vào Graph chính.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ trace/scorecard.

1. **FastAPI MCP Implementation:** Chuyển đổi MCP Server sang dạng HTTP để thực hiện đúng tiêu chuẩn của Model Context Protocol, thay vì dùng Mock Class.
2. **Self-Correction Logic:** Thêm một node "Reflection" sau Synthesis để robot tự kiểm tra xem câu trả lời có vi phạm chính sách của Policy worker hay không trước khi gửi cho người dùng.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
