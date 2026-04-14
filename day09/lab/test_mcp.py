# -*- coding: utf-8 -*-
"""
Comprehensive test script for mcp_server.py (Phase 3)
Tests all tools, edge cases, contract compliance, and trace metadata.
"""
import sys
import os

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure imports work
sys.path.insert(0, os.path.dirname(__file__))

from mcp_server import dispatch_tool, dispatch_tool_with_trace, list_tools, TOOL_SCHEMAS, MOCK_TICKETS

passed = 0
failed = 0
errors = []

def test(name, condition, detail=""):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        errors.append(f"{name}: {detail}")
        print(f"  [FAIL] {name} -- {detail}")


print("=" * 60)
print("MCP Server - Comprehensive Test Suite")
print("=" * 60)

# ========== TEST 1: list_tools() ==========
print("\n--- Test 1: Tool Discovery (list_tools) ---")
tools = list_tools()
test("list_tools returns list", isinstance(tools, list))
test("list_tools has 4 tools", len(tools) == 4, f"got {len(tools)}")
tool_names = [t["name"] for t in tools]
test("search_kb in tools", "search_kb" in tool_names)
test("get_ticket_info in tools", "get_ticket_info" in tool_names)
test("check_access_permission in tools", "check_access_permission" in tool_names)
test("create_ticket in tools", "create_ticket" in tool_names)
for t in tools:
    test(f"Tool '{t['name']}' has inputSchema", "inputSchema" in t, f"missing inputSchema")

# ========== TEST 2: search_kb ==========
print("\n--- Test 2: search_kb ---")
r = dispatch_tool("search_kb", {"query": "SLA P1", "top_k": 3})
test("search_kb returns dict", isinstance(r, dict))
test("search_kb has 'chunks' key", "chunks" in r, f"keys: {list(r.keys())}")
test("search_kb has 'sources' key", "sources" in r)
test("search_kb has 'total_found' key", "total_found" in r)
if r.get("chunks"):
    test("chunks is non-empty list", len(r["chunks"]) > 0)
    chunk0 = r["chunks"][0]
    test("chunk has 'text'", "text" in chunk0)
    test("chunk has 'source'", "source" in chunk0)
    test("chunk has 'score'", "score" in chunk0)
    test("chunk score is float", isinstance(chunk0["score"], (int, float)))
    test("chunk text contains SLA content", "p1" in chunk0["text"].lower() or "sla" in chunk0["text"].lower(),
         f"text: {chunk0['text'][:80]}")

# Test search_kb with refund query
r2 = dispatch_tool("search_kb", {"query": "hoan tien refund", "top_k": 2})
test("search_kb refund query returns chunks", len(r2.get("chunks", [])) > 0)

# ========== TEST 3: get_ticket_info ==========
print("\n--- Test 3: get_ticket_info ---")
t1 = dispatch_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
test("P1-LATEST returns dict", isinstance(t1, dict))
test("P1-LATEST has ticket_id", "ticket_id" in t1)
test("P1-LATEST ticket_id is IT-9847", t1.get("ticket_id") == "IT-9847", f"got {t1.get('ticket_id')}")
test("P1-LATEST has priority P1", t1.get("priority") == "P1")
test("P1-LATEST has notifications_sent", "notifications_sent" in t1)
test("P1-LATEST has sla_deadline", "sla_deadline" in t1)
test("P1-LATEST created_at is 22:47", "22:47" in t1.get("created_at", ""), f"got {t1.get('created_at')}")

t2 = dispatch_tool("get_ticket_info", {"ticket_id": "IT-1234"})
test("IT-1234 returns valid ticket", t2.get("ticket_id") == "IT-1234")
test("IT-1234 priority is P2", t2.get("priority") == "P2")

t3 = dispatch_tool("get_ticket_info", {"ticket_id": "GQ-01"})
test("GQ-01 returns valid ticket", t3.get("ticket_id") == "IT-2247", f"got {t3.get('ticket_id')}")

# Edge: invalid ticket
t_err = dispatch_tool("get_ticket_info", {"ticket_id": "NONEXISTENT"})
test("Invalid ticket returns error", "error" in t_err)
test("Invalid ticket does NOT crash", True)  # If we got here, it didn't crash

# ========== TEST 4: check_access_permission ==========
print("\n--- Test 4: check_access_permission ---")
p1 = dispatch_tool("check_access_permission", {"access_level": 1, "requester_role": "employee"})
test("Level 1 returns dict", isinstance(p1, dict))
test("Level 1 can_grant is True", p1.get("can_grant") == True)
test("Level 1 has 1 approver", len(p1.get("required_approvers", [])) == 1)

p2 = dispatch_tool("check_access_permission", {"access_level": 2, "requester_role": "contractor", "is_emergency": True})
test("Level 2 emergency: can_grant True", p2.get("can_grant") == True)
test("Level 2 emergency: override True", p2.get("emergency_override") == True)
test("Level 2 has 2 approvers", len(p2.get("required_approvers", [])) == 2)

p3 = dispatch_tool("check_access_permission", {"access_level": 3, "requester_role": "contractor", "is_emergency": True})
test("Level 3 emergency: NO override", p3.get("emergency_override") == False)
test("Level 3 has 3 approvers", len(p3.get("required_approvers", [])) == 3)
test("Level 3 has source field", p3.get("source") == "access_control_sop.txt")

# Edge: invalid level
p_err = dispatch_tool("check_access_permission", {"access_level": 99, "requester_role": "hacker"})
test("Invalid level returns error", "error" in p_err)

# ========== TEST 5: create_ticket ==========
print("\n--- Test 5: create_ticket ---")
ct = dispatch_tool("create_ticket", {"priority": "P1", "title": "Test incident"})
test("create_ticket returns dict", isinstance(ct, dict))
test("create_ticket has ticket_id", "ticket_id" in ct)
test("create_ticket has url", "url" in ct)
test("create_ticket has created_at", "created_at" in ct)

# ========== TEST 6: Error handling ==========
print("\n--- Test 6: Error handling ---")
e1 = dispatch_tool("nonexistent_tool", {})
test("Nonexistent tool returns error dict", isinstance(e1, dict) and "error" in e1)
test("Error mentions available tools", "Available" in e1.get("error", "") or "available" in e1.get("error", "").lower())

e2 = dispatch_tool("get_ticket_info", {})  # Missing required param
test("Missing param returns error", isinstance(e2, dict) and "error" in e2)

# ========== TEST 7: dispatch_tool_with_trace ==========
print("\n--- Test 7: dispatch_tool_with_trace ---")
tr = dispatch_tool_with_trace("get_ticket_info", {"ticket_id": "P1-LATEST"})
test("trace wrapper returns dict", isinstance(tr, dict))
test("trace has 'tool' field", tr.get("tool") == "get_ticket_info")
test("trace has 'input' field", "input" in tr)
test("trace has 'output' field", "output" in tr)
test("trace has 'timestamp' field", "timestamp" in tr)
test("trace has 'error' field (None for success)", "error" in tr and tr["error"] is None)
test("trace output is actual ticket data", tr.get("output", {}).get("ticket_id") == "IT-9847")

# Test trace with error
tr_err = dispatch_tool_with_trace("bad_tool", {})
test("trace error: tool name recorded", tr_err.get("tool") == "bad_tool")
test("trace error: error is not None", tr_err.get("error") is not None)

# ========== TEST 8: Contract compliance ==========
print("\n--- Test 8: Contract compliance (worker_contracts.yaml) ---")
# search_kb output must have: chunks, sources, total_found
r_kb = dispatch_tool("search_kb", {"query": "access control", "top_k": 2})
test("search_kb output has chunks (contract)", "chunks" in r_kb)
test("search_kb output has sources (contract)", "sources" in r_kb)
test("search_kb output has total_found (contract)", "total_found" in r_kb)

# get_ticket_info output must have: ticket_id, priority, status, assignee, created_at, sla_deadline
t_contract = dispatch_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
for field in ["ticket_id", "priority", "status", "assignee", "created_at", "sla_deadline"]:
    test(f"get_ticket_info has '{field}' (contract)", field in t_contract, f"missing {field}")

# check_access_permission output: can_grant, required_approvers, emergency_override, source
p_contract = dispatch_tool("check_access_permission", {"access_level": 2, "requester_role": "dev"})
for field in ["can_grant", "required_approvers", "emergency_override", "source"]:
    test(f"check_access has '{field}' (contract)", field in p_contract, f"missing {field}")

# ========== TEST 9: Keyword fallback quality ==========
print("\n--- Test 9: Keyword fallback quality ---")
# This tests that search_kb can find relevant info from data/docs files
queries_expected_sources = [
    ("SLA P1 escalation", "sla_p1_2026.txt"),
    ("refund policy flash sale", "policy_refund_v4.txt"),
    ("access level 3 emergency", "access_control_sop.txt"),
]
for query, expected_source in queries_expected_sources:
    r = dispatch_tool("search_kb", {"query": query, "top_k": 3})
    sources = r.get("sources", [])
    test(f"query '{query}' finds {expected_source}",
         expected_source in sources,
         f"got sources: {sources}")

# ========== RESULTS ==========
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  - {e}")

if failed == 0:
    print("\nAll tests passed!")
else:
    print(f"\n{failed} test(s) need fixing.")
