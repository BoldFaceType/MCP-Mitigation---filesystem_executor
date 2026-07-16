import asyncio
import json
from pathlib import Path
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from homecmd.acp import create_acp_app
from homecmd.app import HomecmdService
from homecmd.audit import AuditLog
from homecmd.executor import CommandExecutor
from homecmd.policy import PolicyEngine
from homecmd.registry import CommandRegistry
from homecmd.server import validate_bind


def make_service(tmp_path: Path, *, risk: str = "read") -> HomecmdService:
    commands = tmp_path / "commands.toml"
    commands.write_text(
        f'''\
[[commands]]
id = "test.echo"
summary = "Echo a message"
risk = "{risk}"
argv = ["@python", "-c", "import sys; print(sys.argv[1])", "{{message}}"]

[[commands.arguments]]
name = "message"
type = "string"
required = true
''',
        encoding="utf-8",
    )
    registry = CommandRegistry.from_paths([commands])
    audit = AuditLog(tmp_path / "audit.jsonl")
    executor = CommandExecutor(registry, PolicyEngine.read_only(), audit)
    return HomecmdService(registry, executor, audit)


def acp_input(payload: dict) -> dict:
    return {
        "agent_name": "homecmd-agent",
        "mode": "sync",
        "input": [{
            "role": "user",
            "parts": [{
                "content_type": "text/plain",
                "content": json.dumps(payload),
            }],
        }],
    }


def test_acp_discovers_only_homecmd_agent(tmp_path: Path) -> None:
    client = TestClient(create_acp_app(make_service(tmp_path)))

    response = client.get("/agents")

    assert response.status_code == 200
    assert [agent["name"] for agent in response.json()["agents"]] == ["homecmd-agent"]


def test_acp_run_uses_same_service_as_cli(tmp_path: Path) -> None:
    client = TestClient(create_acp_app(make_service(tmp_path)))

    response = client.post("/runs", json=acp_input({
        "operation": "run",
        "command_id": "test.echo",
        "args": {"message": "hello-acp"},
    }))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["created_at"].endswith("+00:00")
    part = body["output"][0]["parts"][0]
    assert part["content_type"] == "application/json"
    assert json.loads(part["content"])["stdout"] == "hello-acp\n"


def test_acp_rejects_unknown_operation(tmp_path: Path) -> None:
    client = TestClient(create_acp_app(make_service(tmp_path)))

    response = client.post("/runs", json=acp_input({"operation": "execute_shell"}))

    assert response.status_code == 400


def test_acp_requires_configured_bearer_token(tmp_path: Path) -> None:
    client = TestClient(create_acp_app(make_service(tmp_path), token="correct-token"))

    missing = client.get("/agents")
    wrong = client.get("/agents", headers={"Authorization": "Bearer wrong-token"})
    accepted = client.get("/agents", headers={"Authorization": "Bearer correct-token"})

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert accepted.status_code == 200


def test_non_loopback_bind_requires_token() -> None:
    with pytest.raises(ValueError, match="token"):
        validate_bind("0.0.0.0", token=None, tls_terminated=False)

    with pytest.raises(ValueError, match="TLS"):
        validate_bind("0.0.0.0", token="configured", tls_terminated=False)

    validate_bind("0.0.0.0", token="configured", tls_terminated=True)


def test_acp_app_does_not_expose_legacy_execution_routes(tmp_path: Path) -> None:
    client = TestClient(create_acp_app(make_service(tmp_path)))

    assert client.post("/execute", json={"code": "print('unsafe')"}).status_code == 404
    assert client.get("/files/list").status_code == 404
    assert client.post("/mqtt/publish", json={}).status_code == 404
    assert client.post("/mcp", json={}).status_code == 404


def test_acp_maps_policy_denial_to_forbidden(tmp_path: Path) -> None:
    client = TestClient(create_acp_app(make_service(tmp_path, risk="write")), raise_server_exceptions=False)

    response = client.post("/runs", json=acp_input({
        "operation": "run",
        "command_id": "test.echo",
        "args": {"message": "blocked"},
    }))

    assert response.status_code == 403


def test_acp_rejects_messages_without_parts(tmp_path: Path) -> None:
    client = TestClient(create_acp_app(make_service(tmp_path)), raise_server_exceptions=False)
    request = acp_input({"operation": "search", "query": "echo"})
    request["input"][0]["parts"] = []

    response = client.post("/runs", json=request)

    assert response.status_code == 400


def test_acp_compacts_large_run_output_but_log_retains_it(tmp_path: Path) -> None:
    commands = tmp_path / "commands.toml"
    commands.write_text(
        '''\
[[commands]]
id = "test.large"
summary = "Return output larger than the ACP preview"
risk = "read"
argv = ["@python", "-c", "print('x' * 6000)"]
max_output_chars = 7000
''',
        encoding="utf-8",
    )
    registry = CommandRegistry.from_paths([commands])
    audit = AuditLog(tmp_path / "audit.jsonl")
    service = HomecmdService(
        registry,
        CommandExecutor(registry, PolicyEngine.read_only(), audit),
        audit,
    )
    client = TestClient(create_acp_app(service))

    run_response = client.post("/runs", json=acp_input({
        "operation": "run",
        "command_id": "test.large",
        "args": {},
    }))
    run_result = json.loads(run_response.json()["output"][0]["parts"][0]["content"])
    log_response = client.post("/runs", json=acp_input({
        "operation": "log",
        "run_id": run_result["run_id"],
    }))
    log_result = json.loads(log_response.json()["output"][0]["parts"][0]["content"])

    assert len(run_result["stdout"]) == 4000
    assert run_result["truncated"] is True
    assert len(log_result["stdout"]) == 6001


def test_acp_rejects_url_content_for_command_operations(tmp_path: Path) -> None:
    client = TestClient(create_acp_app(make_service(tmp_path)), raise_server_exceptions=False)
    request = acp_input({"operation": "search", "query": "echo"})
    request["input"][0]["parts"][0].pop("content")
    request["input"][0]["parts"][0]["content_url"] = "https://example.invalid/payload.json"

    response = client.post("/runs", json=request)

    assert response.status_code == 400


def test_acp_runs_blocking_commands_off_the_event_loop(tmp_path: Path) -> None:
    commands = tmp_path / "commands.toml"
    commands.write_text(
        '''\
[[commands]]
id = "test.sleep"
summary = "Sleep briefly"
risk = "read"
argv = ["@python", "-c", "import time; time.sleep(0.5); print('done')"]
''',
        encoding="utf-8",
    )
    registry = CommandRegistry.from_paths([commands])
    audit = AuditLog(tmp_path / "audit.jsonl")
    app = create_acp_app(HomecmdService(
        registry,
        CommandExecutor(registry, PolicyEngine.read_only(), audit),
        audit,
    ))

    async def run_two() -> list[httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            request = acp_input({"operation": "run", "command_id": "test.sleep", "args": {}})
            return await asyncio.gather(client.post("/runs", json=request), client.post("/runs", json=request))

    started = time.monotonic()
    responses = asyncio.run(run_two())
    elapsed = time.monotonic() - started

    assert [response.status_code for response in responses] == [200, 200]
    assert elapsed < 0.85
