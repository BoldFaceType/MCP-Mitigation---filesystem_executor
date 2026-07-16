"""Run a live bounded MCP worker call through the shipping server."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


TASK = "Confirm briefly that the bounded local worker is active."


def reserve_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def post_json(url: str, payload: dict, timeout: int = 130) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_health(url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else ""
            raise RuntimeError(f"homecmd-agent exited before startup: {stderr}")
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("homecmd-agent did not become healthy")


def process_options() -> dict:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def stop_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_smoke(url: str) -> dict:
    initialized = post_json(url, {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "homecmd-worker-smoke", "version": "1.0"},
        },
    })
    if initialized["result"]["protocolVersion"] != "2025-06-18":
        raise RuntimeError(f"unexpected MCP protocol: {initialized}")
    tools = post_json(url, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    })
    tool_names = [tool["name"] for tool in tools["result"]["tools"]]
    if tool_names != ["call_worker"]:
        raise RuntimeError(f"unexpected worker tools: {tool_names}")
    call = post_json(url, {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "call_worker",
            "arguments": {"task": TASK, "max_output_chars": 1000, "timeout_seconds": 120},
        },
    })
    result = call["result"]
    worker = json.loads(result["content"][0]["text"])
    if result["isError"] or not worker.get("ok") or not worker.get("result"):
        raise RuntimeError(f"bounded worker call failed: {worker}")
    return {"tools": tool_names, "worker": worker}


def main() -> int:
    port = reserve_port()
    url = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="homecmd-worker-smoke-") as temp_dir:
        audit_path = Path(temp_dir) / "audit.jsonl"
        env = os.environ.copy()
        env["HOMECMD_PORT"] = str(port)
        env["HOMECMD_AUDIT_LOG"] = str(audit_path)
        process = subprocess.Popen(
            [sys.executable, "-m", "homecmd.server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            **process_options(),
        )
        try:
            wait_for_health(url, process)
            evidence = run_smoke(f"{url}/mcp")
            audit_text = audit_path.read_text(encoding="utf-8")
            if TASK in audit_text:
                raise RuntimeError("worker audit persisted task content")
        finally:
            stop_process_tree(process)
    print(json.dumps({
        "tools": evidence["tools"],
        "worker_id": evidence["worker"]["worker_id"],
        "run_id": evidence["worker"]["run_id"],
        "output_chars": len(evidence["worker"]["result"]),
        "prompt_persisted": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
