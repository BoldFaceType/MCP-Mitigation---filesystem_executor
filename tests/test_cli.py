import json
from io import StringIO
from pathlib import Path

from homecmd.app import HomecmdService
from homecmd.audit import AuditLog
from homecmd.cli import main
from homecmd.executor import CommandExecutor
from homecmd.policy import PolicyEngine
from homecmd.registry import CommandRegistry


def make_service(tmp_path: Path) -> HomecmdService:
    commands = tmp_path / "commands.toml"
    commands.write_text(
        '''\
[[commands]]
id = "test.echo"
summary = "Echo a message"
risk = "read"
argv = ["@python", "-c", "import sys; print(sys.argv[1])", "{message}"]

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


def invoke(service: HomecmdService, *args: str) -> tuple[int, object]:
    output = StringIO()
    exit_code = main(list(args), service=service, stdout=output)
    return exit_code, json.loads(output.getvalue())


def test_cli_search_returns_compact_results(tmp_path: Path) -> None:
    code, payload = invoke(make_service(tmp_path), "search", "echo")

    assert code == 0
    assert payload == [{
        "id": "test.echo",
        "summary": "Echo a message",
        "risk": "read",
        "args": ["message"],
    }]


def test_cli_card_returns_selected_card(tmp_path: Path) -> None:
    code, payload = invoke(make_service(tmp_path), "card", "test.echo")

    assert code == 0
    assert payload["id"] == "test.echo"
    assert payload["argv"][-1] == "{message}"


def test_cli_run_then_log_returns_same_run(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    run_code, run_payload = invoke(service, "run", "test.echo", "message=hello")
    log_code, log_payload = invoke(service, "log", run_payload["run_id"])

    assert run_code == 0
    assert run_payload["stdout"] == "hello\n"
    assert log_code == 0
    assert log_payload["run_id"] == run_payload["run_id"]
    assert log_payload["command_id"] == "test.echo"


def test_cli_rejects_malformed_key_value_argument(tmp_path: Path) -> None:
    output = StringIO()

    code = main(
        ["run", "test.echo", "not-key-value"],
        service=make_service(tmp_path),
        stdout=output,
    )

    assert code == 2
    assert json.loads(output.getvalue())["error"] == "invalid_argument"
