#!/usr/bin/env python3
"""
Standalone test script for mcp-mitigation endpoints.
Run from the host: python scripts/test_tools.py

Hard-fail tests: 1-7
Soft-fail test:  8 (MQTT publish — broker may not be up)
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
WARN = "\033[33mWARN\033[0m"

failures = 0


def _request(method: str, path: str, body=None, params: dict | None = None) -> dict:
    url = BASE + path
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url += "?" + qs
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


import urllib.parse


def check(label: str, condition: bool, detail: str = ""):
    global failures
    if condition:
        print(f"  {PASS}  {label}")
    else:
        print(f"  {FAIL}  {label}" + (f" — {detail}" if detail else ""))
        failures += 1


def soft_warn(label: str, detail: str = ""):
    print(f"  {WARN}  {label}" + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------------------
print("\n=== mcp-mitigation tool tests ===\n")

# Test 1: /health
print("1. GET /health")
try:
    data = _request("GET", "/health")
    check("status == ok", data.get("status") == "ok", str(data))
except Exception as e:
    check("GET /health reachable", False, str(e))

# Test 2: /execute python
print("2. POST /execute  python  print(1+1)")
try:
    data = _request("POST", "/execute", {"code": "print(1+1)", "language": "python"})
    check("result == '2\\n'", data.get("result") == "2\n", str(data))
except Exception as e:
    check("/execute python", False, str(e))

# Test 3: /execute shell
print("3. POST /execute  shell  echo hello")
try:
    data = _request("POST", "/execute", {"code": "echo hello", "language": "shell"})
    check("result == 'hello\\n'", data.get("result") == "hello\n", str(data))
except Exception as e:
    check("/execute shell", False, str(e))

# Test 4: /files/list
print("4. GET /files/list?path=.")
try:
    data = _request("GET", "/files/list", params={"path": "."})
    entries = data.get("entries", [])
    check("non-empty list", isinstance(entries, list) and len(entries) > 0, str(data))
except Exception as e:
    check("/files/list", False, str(e))

# Test 5: /files/write
print("5. POST /files/write  _test_mcp.txt")
try:
    data = _request("POST", "/files/write", {"path": "_test_mcp.txt", "content": "hello"})
    check("message present", "message" in data, str(data))
except Exception as e:
    check("/files/write", False, str(e))

# Test 6: /files/read
print("6. GET /files/read?path=_test_mcp.txt")
try:
    data = _request("GET", "/files/read", params={"path": "_test_mcp.txt"})
    check("content == 'hello'", data.get("content") == "hello", str(data))
except Exception as e:
    check("/files/read", False, str(e))

# Test 7: cleanup via /execute shell
print("7. Cleanup  rm _test_mcp.txt")
try:
    data = _request("POST", "/execute", {"code": "rm /workspace/_test_mcp.txt", "language": "shell"})
    check("no error", not data.get("error"), str(data))
except Exception as e:
    check("cleanup via /execute", False, str(e))

# Test 8: /mqtt/publish (soft-fail)
print("8. POST /mqtt/publish  chillloop/health/mcp-test  (soft-fail)")
try:
    data = _request("POST", "/mqtt/publish", {
        "host": "mqtt.local",
        "port": 1883,
        "user": "chillloop",
        "password": "",
        "topic": "chillloop/health/mcp-test",
        "payload": "mcp-mitigation test ok",
        "retain": False,
    })
    check("published ok", "message" in data, str(data))
except urllib.error.HTTPError as e:
    soft_warn("MQTT broker unreachable (502) — skipped", str(e))
except Exception as e:
    soft_warn("MQTT publish skipped", str(e))

# ---------------------------------------------------------------------------
print()
if failures:
    print(f"RESULT: {failures} hard failure(s). See above.")
    sys.exit(1)
else:
    print("RESULT: all hard tests passed.")
