# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Đức Duy
**Vai trò trong nhóm:** Supervisor Owner & Docs Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào?

**Module/file tôi chịu trách nhiệm:**
- File chính: `graph.py` (Bộ định tuyến gốc của hệ thống) và `docs/system_architecture.md` (Tài liệu kiến trúc).
- Functions tôi implement: `supervisor_node()` và `build_graph()` trong `graph.py` nhằm xây dựng mạng lưới đường đi của AgentState dựa trên StateGraph. Chịu trách nhiệm thiết lập từ khóa cho các Node đích.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Routing logic do tôi viết quyết định thẳng việc các node của những người khác (`retrieval_worker`, `policy_tool_worker`, `synthesis_worker`) có được gọi và có được cấp cờ kích hoạt công cụ bên ngoài (`needs_tool=True`) hay không. Nếu logic của tôi sai, các worker khác sẽ không nhận được dữ liệu Input đầu vào chuẩn xác. Thêm vào đó, thông qua việc thu thập Contract từ team, tôi đã ráp nối để hoàn thiện sơ đồ mô tả `system_architecture.md` thành một thể thống nhất cho toàn đồ án báo cáo.

**Bằng chứng:**
- Commit / File edit tại `graph.py` tại method `supervisor_node(state)`.
- Chỉnh sửa `system_architecture.md` bằng Mermaid schema thực tế.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Tôi chọn dùng **Keyword-based Routing** (định dạng String matching thủ công qua mảng mảng text `policy_keywords` và `retrieval_keywords`) cho Node Supervisor thay vì sử dụng gọi API qua mô hình LLM.

**Lý do:**
1. **Tốc độ (Latency):** Supervisor đóng vai trò trạm chuyển tiếp nội bộ. Nếu mọi query đều gọi LLM để lấy hướng đi, độ trễ sẽ đội lên thêm từ 800ms tới 1.5s làm giảm UX người dùng. Keyword matching giải quyết routing trong 0ms.
2. **Deterministic (Tính tất định):** Bằng cách chặn strict các từ khoá (như "hoàn tiền", "flash sale", "P1", "err-"), tôi khử hoàn toàn ảo giác (hallucination) thường gặp ở LLM, đảm bảo lệnh lỗi hệ thống luôn đi tới Node Human Review thay vì đi khuyên dùng tài liệu cơ bản.

**Trade-off đã chấp nhận:** Đánh đổi đi tính linh hoạt Semantic logic. Nếu user gõ sai chính tả (vd: "hoèng tiền" thay vì "hoàn tiền"), hệ thống sẽ có rủi ro bị route vào nhánh `retrieval_worker` thay vì báo vi phạm điều khoản công ty.

**Bằng chứng từ trace/code:**
Trích xuất đoạn mã đã chèn để cấu trúc Route trong vòng eo Supervisor:
```python
    policy_keywords = ["hoàn tiền", "refund", "flash sale", "license", "cấp quyền", "access level", "level 3"]
    if any(kw in task for kw in policy_keywords):
        route = "policy_tool_worker"
        route_reason = "task contains policy or access-level keywords"
        needs_tool = True
```
Trace đầu ra minh chứng: `Route: policy_tool_worker | Reason: task contains policy or access-level keywords | Latency: 0ms.`

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:**  `UnicodeDecodeError: 'charmap' codec can't decode...` khi chạy test và Index Vector Database ChromaDB lần đầu tiên trên Windows Terminal.

**Symptom (pipeline làm gì sai?):**  
Khi chạy Python Setup script để đánh chỉ mục (Index) các file trong thư mục `docs/`, hệ thống báo lỗi không thể nạp các file văn bản chứa ký tự tiếng Việt. Dòng lệnh báo sập ngay sau file số 2.

**Root cause:**  
File text chứa Tiếng Việt utf-8. Tuy nhiên do môi trường là Windows, hàm `open()` tích hợp mặc định dùng bộ mã Encoding `cp1252`. Do đó khi dùng lệnh `.read()` hệ thống đã Crash do kí tự không được hỗ trợ.

**Cách sửa:**  
Tôi đã bắt tận tay và sửa trực tiếp tại File script bằng cách tiêm tham số cứng `encoding="utf-8"`. 

**Bằng chứng trước/sau:**
Trước khi sửa (Lỗi vỡ Script python bị treo Terminal Windows):
```python
with open(os.path.join(docs_dir, fname)) as f:
```
Sau khi sửa (Chạy hoàn thành mượt mà toàn bộ 5 file):
```python
with open(os.path.join(docs_dir, fname), encoding='utf-8') as f:
```

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**
Tôi làm tốt phần kiến tạo cấu trúc móng vững chắc qua việc bóc tách `AgentState` và gán ghép mô hình I/O YAML Contracts logic. Nó giúp cả team C401 - A3 phát triển song song hoàn hảo (các role Worker thoải mái test độc lập mà không cần quan tâm đến lỗi điều tiết luồng bên ngoài).

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Do dùng Keyword routing nên cơ chế bắt ý định (Intent Classification) vẫn còn phụ thuộc thụ động vào một bộ mảng test queries và chưa bao phủ được độ phức tạp thực tiễn của một cuộc trò chuyện dài.

**Nhóm phụ thuộc vào tôi ở đâu?**
Sự gắn kết. Mọi team như Retrieval, Policy, Synthesis đều bị Block quy trình chạy end-to-end cho đến khi tôi mở khóa comment gọi import hàm tương ứng và thiết lập đúng Router ở `build_graph()`.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần các bạn ở Phase 2, 3 ,4 tuân thủ chặt format đầu ra YAML List/Dict/Boolean đã được thiết kế sẵn để truyền vào chung State Graph thì `synthesis.py` (của Phase 5) mới sinh Answer thành công.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ bắt tay vào việc bỏ Router bằng Regex String Match để thử nghiệm nâng cấp bằng mô hình LLM Semantic Router cục bộ nhẹ nhành (như dùng thư viện Outlines) để Supervisor có thể hiểu và route câu hỏi ngay cả khi người dùng không cung cấp chính xác từ khoá tĩnh. Bằng chứng được thể hiện khi test case người dùng gõ sai chính tả khiến nó bypass lọt vào nhầm Default Retrieval Fallback.