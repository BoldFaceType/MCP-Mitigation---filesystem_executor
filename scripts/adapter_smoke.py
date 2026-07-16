"""Run a live ACP-to-MCP adapter compatibility smoke test."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from queue import Empty, Queue
from threading import Thread
import time
import urllib.request
from pathlib import Path


ADAPTER_PACKAGE = "acp-mcp==0.4.2"
ACP_SDK_PACKAGE = "acp-sdk==0.8.4"


def reserve_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_for_health(url: str, server: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if server.poll() is not None:
            stderr = server.stderr.read() if server.stderr else ""
            raise RuntimeError(f"homecmd-agent exited before startup: {stderr}")
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("homecmd-agent did not become healthy")


def mcp_messages() -> list[dict]:
    return [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "homecmd-smoke", "version": "1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "run_agent",
                "arguments": {
                    "agent": "homecmd-agent",
                    "input": [{
                        "role": "user",
                        "parts": [{
                            "content_type": "application/json",
                            "content": json.dumps({
                                "operation": "run",
                                "command_id": "system.python_version",
                                "args": {},
                            }, separators=(",", ":")),
                        }],
                    }],
                },
            },
        },
    ]


def mcp_input() -> str:
    return "".join(
        json.dumps(message, separators=(",", ":")) + "\n"
        for message in mcp_messages()
    )


def parse_adapter_output(stdout: str) -> tuple[list[dict], dict]:
    responses = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    tool_response = next((item for item in responses if item.get("id") == 2), None)
    if tool_response is None:
        raise RuntimeError(f"adapter returned no tools/list response: {stdout}")
    if "error" in tool_response:
        raise RuntimeError(f"adapter tools/list failed: {tool_response['error']}")
    call_response = next((item for item in responses if item.get("id") == 3), None)
    if call_response is None:
        raise RuntimeError(f"adapter returned no tools/call response: {stdout}")
    if "error" in call_response:
        raise RuntimeError(f"adapter tools/call failed: {call_response['error']}")
    return tool_response["result"]["tools"], call_response["result"]


def _read_stdout(stream, output: Queue[str]) -> None:
    for line in stream:
        output.put(line)


def _send(process: subprocess.Popen[str], message: dict) -> None:
    if process.stdin is None:
        raise RuntimeError("adapter stdin is unavailable")
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def _read_response(output: Queue[str], request_id: int, timeout: int = 30) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            line = output.get(timeout=min(1, deadline - time.monotonic()))
        except Empty:
            continue
        response = json.loads(line)
        if response.get("id") == request_id:
            return response
    raise TimeoutError(f"adapter did not answer request {request_id}")


def _popen_group_options() -> dict:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _stop_process_tree(process: subprocess.Popen[str]) -> None:
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


def run_adapter(adapter: str, url: str) -> tuple[list[dict], dict, str]:
    process = subprocess.Popen(
        [
            adapter,
            "--with",
            ACP_SDK_PACKAGE,
            ADAPTER_PACKAGE,
            "--log-level",
            "ERROR",
            url,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **_popen_group_options(),
    )
    if process.stdout is None:
        raise RuntimeError("adapter stdout is unavailable")
    output: Queue[str] = Queue()
    Thread(target=_read_stdout, args=(process.stdout, output), daemon=True).start()
    initialize, initialized, tools_list, tools_call = mcp_messages()
    try:
        _send(process, initialize)
        initialize_response = _read_response(output, 1)
        if "error" in initialize_response:
            raise RuntimeError(f"adapter initialize failed: {initialize_response['error']}")
        _send(process, initialized)
        _send(process, tools_list)
        tools_response = _read_response(output, 2)
        _send(process, tools_call)
        call_response = _read_response(output, 3)
    finally:
        _stop_process_tree(process)
    stderr = process.stderr.read() if process.stderr else ""
    combined = "\n".join(json.dumps(item) for item in (tools_response, call_response))
    tools, call_result = parse_adapter_output(combined)
    return tools, call_result, stderr


def main() -> int:
    adapter = shutil.which("uvx")
    if not adapter:
        raise RuntimeError("uvx is required; install uv before running this smoke test")
    port = reserve_port()
    url = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="homecmd-smoke-") as temp_dir:
        env = os.environ.copy()
        env["HOMECMD_PORT"] = str(port)
        env["HOMECMD_AUDIT_LOG"] = str(Path(temp_dir) / "audit.jsonl")
        server = subprocess.Popen(
            [sys.executable, "-m", "homecmd.server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            **_popen_group_options(),
        )
        try:
            wait_for_health(url, server)
            tools, call_result, stderr = run_adapter(adapter, url)
        finally:
            _stop_process_tree(server)
    tool_names = [tool["name"] for tool in tools]
    if "run_agent" not in tool_names:
        raise RuntimeError(f"adapter did not expose run_agent: {tool_names}")
    run_agent = next(tool for tool in tools if tool["name"] == "run_agent")
    rendered_call = json.dumps(call_result, separators=(",", ":"))
    if call_result.get("isError") or "system.python_version" not in rendered_call:
        raise RuntimeError(f"run_agent did not execute the registered command: {call_result}")
    print(json.dumps({
        "adapter": ADAPTER_PACKAGE,
        "acp_sdk": ACP_SDK_PACKAGE,
        "tools": tool_names,
        "run_agent_required": run_agent["inputSchema"].get("required", []),
        "executed_command": "system.python_version",
        "stderr": stderr.strip(),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
