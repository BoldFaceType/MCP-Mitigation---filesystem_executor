import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from homecmd.audit import AuditLog
from homecmd.worker import (
    CallWorkerRequest,
    CallWorkerResponse,
    LMStudioWorker,
    install_worker_mcp,
)
from homecmd.server import create_server_app


class StubWorker:
    def call(self, request: CallWorkerRequest) -> CallWorkerResponse:
        return CallWorkerResponse(
            ok=True,
            worker_id="lmstudio.default",
            run_id="stub-run",
            summary=request.task,
            result="bounded-result",
        )


def test_worker_mcp_exposes_only_call_worker() -> None:
    app = FastAPI()
    install_worker_mcp(app, StubWorker())
    client = TestClient(app)

    response = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    })

    assert response.status_code == 200
    assert [tool["name"] for tool in response.json()["result"]["tools"]] == ["call_worker"]


def test_worker_mcp_calls_only_bounded_worker() -> None:
    app = FastAPI()
    install_worker_mcp(app, StubWorker())
    client = TestClient(app)

    response = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "call_worker",
            "arguments": {"task": "summarize", "context": "local context"},
        },
    })

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"])["result"] == "bounded-result"

    rejected = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "cmd_run", "arguments": {}},
    })
    assert rejected.json()["error"]["code"] == -32602


def test_lmstudio_worker_bounds_output_and_omits_prompt_from_audit(tmp_path: Path) -> None:
    calls: list[tuple[str, dict | None, int]] = []

    def request_json(path: str, payload: dict | None, timeout: int) -> dict:
        calls.append((path, payload, timeout))
        if path == "/models":
            return {"data": [{"id": "local-chat-model"}]}
        return {"choices": [{"message": {"content": "abcdefghij"}}]}

    audit = AuditLog(tmp_path / "audit.jsonl")
    worker = LMStudioWorker(
        audit=audit,
        request_json=request_json,
        max_output_chars=8,
        timeout_seconds=30,
    )

    response = worker.call(CallWorkerRequest(
        task="private task text",
        context="private context text",
        max_output_chars=5,
        timeout_seconds=10,
    ))

    assert response.ok is True
    assert response.result == "abcde"
    assert response.truncated is True
    assert [call[0] for call in calls] == ["/models", "/chat/completions"]
    audit_text = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert "private task text" not in audit_text
    assert "private context text" not in audit_text
    assert "local-chat-model" in audit_text


def test_shipping_app_installs_separate_worker_endpoint(tmp_path: Path) -> None:
    app = create_server_app(worker=StubWorker(), audit_path=tmp_path / "audit.jsonl")
    client = TestClient(app)

    agents = client.get("/agents")
    tools = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    })

    assert agents.status_code == 200
    assert [agent["name"] for agent in agents.json()["agents"]] == ["homecmd-agent"]
    assert [tool["name"] for tool in tools.json()["result"]["tools"]] == ["call_worker"]
