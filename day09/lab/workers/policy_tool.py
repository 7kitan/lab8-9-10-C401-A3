"""
workers/policy_tool.py — Policy & Tool Worker
Sprint 2+3: Kiểm tra policy dựa vào context, gọi MCP tools khi cần.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: context từ retrieval_worker
    - needs_tool: True nếu supervisor quyết định cần tool call

Output (vào AgentState):
    - policy_result: {"policy_applies", "policy_name", "exceptions_found", "source", "rule"}
    - mcp_tools_used: list of tool calls đã thực hiện
    - worker_io_log: log

Gọi độc lập để test:
    python workers/policy_tool.py
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, List, Dict
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

WORKER_NAME = "policy_tool_worker"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_llm_policy_analysis(task: str, contexts: List[str]) -> Dict:
    """
    Sử dụng LLM để phân tích chính sách và tìm ngoại lệ.
    """
    system_prompt = """You are an internal Policy Analyst. 
Your task is to check if the user's request violates any internal policies based on the provided documents.

IMPORTANT: Respond in the same language as the provided context documents (primarily Vietnamese).

EXCEPTIONS TO CHECK:
1. Flash Sale: Flash Sale orders are NOT eligible for refunds.
2. Digital Products/Services: License keys, subscriptions, and activated software are NOT eligible for refunds.
3. Timing: Refund requests must be made within 7 working days. Orders placed before Feb 01, 2026, follow the old policy (v3).
4. Access Control: Level 3 access requires 3 approvers and does NOT have an emergency bypass. Level 2 can be bypassed in case of an emergency.

OUTPUT REQUIREMENTS (JSON):
{
  "policy_applies": boolean, (True if allowed/valid, False if blocked/violation)
  "policy_name": string, (Name of the applicable policy)
  "exceptions_found": [
    {"type": string, "rule": string, "source": string}
  ],
  "policy_version_note": string, (Notes on policy version if there is any temporal scoping issue)
  "explanation": string (Brief explanation in the same language as the documents)
}"""

    context_str = "\n---\n".join(contexts)
    user_prompt = f"User Task: {task}\n\nContext Documents:\n{context_str}"

    try:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return None


# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Thay bằng real MCP call
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool.

    Sprint 3 TODO: Implement bằng cách import mcp_server hoặc gọi HTTP.

    Hiện tại: Import trực tiếp từ mcp_server.py (trong-process mock).
    """
    from datetime import datetime

    try:
        # TODO Sprint 3: Thay bằng real MCP client nếu dùng HTTP server
        from mcp_server import dispatch_tool
        result = dispatch_tool(tool_name, tool_input)
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": None,
            "error": {"code": "MCP_CALL_FAILED", "reason": str(e)},
            "timestamp": datetime.now().isoformat(),
        }


# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

def analyze_policy(task: str, chunks: list) -> dict:
    """
    Phân tích policy dựa trên context chunks.

    TODO Sprint 2: Implement logic này với LLM call hoặc rule-based check.

    Cần xử lý các exceptions:
    - Flash Sale → không được hoàn tiền
    - Digital product / license key / subscription → không được hoàn tiền
    - Sản phẩm đã kích hoạt → không được hoàn tiền
    - Đơn hàng trước 01/02/2026 → áp dụng policy v3 (không có trong docs)

    Returns:
        dict with: policy_applies, policy_name, exceptions_found, source, rule, explanation
    """
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks]).lower()

    # --- Step 1: Rule-based fallback/preprocessing ---
    exceptions_found = []

    # Exception check logic (giữ lại làm nền tảng hoặc validation)
    if "flash sale" in task_lower or "flash sale" in context_text:
        exceptions_found.append({
            "type": "flash_sale_exception",
            "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            "source": "policy_refund_v4.txt",
        })

    # --- Step 2: Call LLM for primary analysis ---
    contexts = [c.get("text", "") for c in chunks]
    llm_result = call_llm_policy_analysis(task, contexts)

    if llm_result:
        # Sử dụng kết quả từ LLM nếu thành công
        return {
            "policy_applies": llm_result.get("policy_applies", False),
            "policy_name": llm_result.get("policy_name", "unknown"),
            "exceptions_found": llm_result.get("exceptions_found", []),
            "source": list({c.get("source", "unknown") for c in chunks if c}),
            "policy_version_note": llm_result.get("policy_version_note", ""),
            "explanation": llm_result.get("explanation", "Analyzed via LLM."),
        }

    # --- Step 3: Fallback to rule-based if LLM fails ---
    policy_applies = len(exceptions_found) == 0
    policy_name = "refund_policy_v4"
    policy_version_note = ""
    if any(kw in task_lower for kw in ["31/01", "30/01", "trước 01/02"]):
        policy_version_note = "Đơn hàng đặt trước 01/02/2026 áp dụng chính sách v3."

    sources = list({c.get("source", "unknown") for c in chunks if c})

    return {
        "policy_applies": policy_applies,
        "policy_name": policy_name,
        "exceptions_found": exceptions_found,
        "source": sources,
        "policy_version_note": policy_version_note,
        "explanation": "Analyzed via rule-based fallback (LLM failed).",
    }


# ─────────────────────────────────────────────
# Worker Entry Point
# ─────────────────────────────────────────────

def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với policy_result và mcp_tools_used
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    needs_tool = state.get("needs_tool", False)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("mcp_tools_used", [])

    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "needs_tool": needs_tool,
        },
        "output": None,
        "error": None,
    }

    try:
        task_lower = task.lower()

        # Step 1: Nếu cần tool call (Supervisor flagged needs_tool=True)
        if needs_tool:
            # Case 1: Cần search thêm kiến thức nếu context thiếu
            if not chunks:
                mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
                state["mcp_tools_used"].append(mcp_result)
                if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                    chunks = mcp_result["output"]["chunks"]
                    state["retrieved_chunks"] = chunks

            # Case 2: Tra cứu quyền truy cập
            if any(kw in task_lower for kw in ["cấp quyền", "access", "permission", "level"]):
                # Trích xuất level từ task (giả định level 1, 2, 3)
                level = 1
                if "level 2" in task_lower: level = 2
                elif "level 3" in task_lower: level = 3
                
                is_emergency = any(kw in task_lower for kw in ["khẩn cấp", "emergency", "2am"])
                
                mcp_result = _call_mcp_tool("check_access_permission", {
                    "access_level": level,
                    "requester_role": "contractor", # Mặc định cho sandbox
                    "is_emergency": is_emergency
                })
                state["mcp_tools_used"].append(mcp_result)

            # Case 3: Tra cứu thông tin ticket
            if any(kw in task_lower for kw in ["ticket", "sự cố", "p1", "it-"]):
                mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
                state["mcp_tools_used"].append(mcp_result)

            # Case 4: Tạo ticket mới (nếu task yêu cầu hành động)
            if any(kw in task_lower for kw in ["tạo ticket", "mở ticket", "create ticket"]):
                mcp_result = _call_mcp_tool("create_ticket", {
                    "priority": "P1" if "p1" in task_lower else "P2",
                    "title": task[:100],
                    "description": task
                })
                state["mcp_tools_used"].append(mcp_result)

        # Step 2: Phân tích policy (LLM-based)
        policy_result = analyze_policy(task, chunks)
        state["policy_result"] = policy_result

        worker_io["output"] = {
            "policy_applies": policy_result["policy_applies"],
            "mcp_calls": len(state["mcp_tools_used"]),
            "policy_name": policy_result["policy_name"]
        }
        state["history"].append(f"[{WORKER_NAME}] logic completed. MCP tools called: {len(state['mcp_tools_used'])}")

    except Exception as e:
        worker_io["error"] = {"code": "POLICY_CHECK_FAILED", "reason": str(e)}
        state["policy_result"] = {"error": str(e)}
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Policy Tool Worker — Standalone Test")
    print("=" * 50)

    test_cases = [
        # --- TEST CASE GỐC ---
        {
            "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
            "retrieved_chunks": [
                {"text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
            "needs_tool": False
        },
        {
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
            "needs_tool": False
        },
        {
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
            "needs_tool": False
        },
        # --- TEST CASE BỔ SUNG (MCP & ACCESS) ---
        {
            "task": "Cần cấp quyền Level 3 khẩn cấp cho contractor khắc phục sự cố.",
            "retrieved_chunks": [],
            "needs_tool": True
        },
        {
            "task": "SLA xử lý ticket P1 là bao lâu?",
            "retrieved_chunks": [],
            "needs_tool": True
        }
    ]

    for tc in test_cases:
        print(f"\n▶ Task: {tc['task']}")
        # Simulating partial AgentState
        state = {
            "task": tc["task"],
            "retrieved_chunks": tc["retrieved_chunks"],
            "needs_tool": tc["needs_tool"],
            "history": [],
            "workers_called": [],
            "mcp_tools_used": []
        }
        
        result = run(state)
        pr = result.get("policy_result", {})
        
        print(f"  policy_applies: {pr.get('policy_applies')}")
        print(f"  policy_name   : {pr.get('policy_name')}")
        if pr.get("exceptions_found"):
            for ex in pr["exceptions_found"]:
                print(f"  exception: {ex.get('type')} — {ex.get('rule', '')[:60]}...")
        
        print(f"  Explanation   : {pr.get('explanation')}")
        print(f"  MCP tools used: {[m['tool'] for m in result.get('mcp_tools_used', [])]}")
        print(f"  History count : {len(result.get('history', []))}")

    print("\n✅ policy_tool_worker test done.")
