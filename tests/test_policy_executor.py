import json
import sys
from pathlib import Path

import pytest

from homecmd.audit import AuditLog
from homecmd.executor import ArgumentValidationError, CommandExecutor
from homecmd.policy import PolicyDenied, PolicyEngine
from homecmd.registry import CommandRegistry


def make_registry(tmp_path: Path, *, risk: str = "read", secret: bool = False) -> CommandRegistry:
    registry_path = tmp_path / "commands.toml"
    registry_path.write_text(
        f'''\
[[commands]]
id = "test.echo"
summary = "Echo one argument"
risk = "{risk}"
argv = ["@python", "-c", "import sys; print(sys.argv[1])", "{{message}}"]
timeout_seconds = 5
max_output_chars = 1000

[[commands.arguments]]
name = "message"
type = "string"
required = true
secret = {str(secret).lower()}
''',
        encoding="utf-8",
    )
    return CommandRegistry.from_paths([registry_path])


def test_executor_keeps_shell_metacharacters_in_one_argument(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    audit = AuditLog(tmp_path / "audit.jsonl")
    executor = CommandExecutor(registry, PolicyEngine.read_only(), audit)
    marker = tmp_path / "must-not-exist"
    hostile = f"hello; {sys.executable} -c open('{marker}','w').write('bad')"

    result = executor.run("test.echo", {"message": hostile})

    assert result.ok is True
    assert result.stdout.strip() == hostile
    assert not marker.exists()


def test_executor_rejects_unknown_arguments(tmp_path: Path) -> None:
    executor = CommandExecutor(
        make_registry(tmp_path),
        PolicyEngine.read_only(),
        AuditLog(tmp_path / "audit.jsonl"),
    )

    with pytest.raises(ArgumentValidationError, match="unknown"):
        executor.run("test.echo", {"message": "ok", "unknown": "value"})


def test_default_policy_denies_write_commands(tmp_path: Path) -> None:
    executor = CommandExecutor(
        make_registry(tmp_path, risk="write"),
        PolicyEngine.read_only(),
        AuditLog(tmp_path / "audit.jsonl"),
    )

    with pytest.raises(PolicyDenied, match="write"):
        executor.run("test.echo", {"message": "blocked"})


def test_policy_loads_allowed_risks_from_toml(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text('allowed_risks = ["read", "write"]\n', encoding="utf-8")

    policy = PolicyEngine.from_toml(path)

    policy.authorize(make_registry(tmp_path, risk="write").get("test.echo"))


def test_executor_truncates_output(tmp_path: Path) -> None:
    path = tmp_path / "commands.toml"
    path.write_text(
        '''\
[[commands]]
id = "test.long"
summary = "Return long output"
risk = "read"
argv = ["@python", "-c", "print('x' * 100)"]
max_output_chars = 20
''',
        encoding="utf-8",
    )
    executor = CommandExecutor(
        CommandRegistry.from_paths([path]),
        PolicyEngine.read_only(),
        AuditLog(tmp_path / "audit.jsonl"),
    )

    result = executor.run("test.long", {})

    assert result.truncated is True
    assert len(result.stdout) == 20


def test_executor_reports_timeout(tmp_path: Path) -> None:
    path = tmp_path / "commands.toml"
    path.write_text(
        '''\
[[commands]]
id = "test.slow"
summary = "Sleep too long"
risk = "read"
argv = ["@python", "-c", "import time; time.sleep(2)"]
timeout_seconds = 1
''',
        encoding="utf-8",
    )
    executor = CommandExecutor(
        CommandRegistry.from_paths([path]),
        PolicyEngine.read_only(),
        AuditLog(tmp_path / "audit.jsonl"),
    )

    result = executor.run("test.slow", {})

    assert result.ok is False
    assert result.error == "timeout"


def test_audit_redacts_secret_arguments_and_output(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    executor = CommandExecutor(
        make_registry(tmp_path, secret=True),
        PolicyEngine.read_only(),
        audit,
    )

    result = executor.run("test.echo", {"message": "top-secret-value"})
    event = audit.get(result.run_id)

    assert event["args"]["message"] == "[REDACTED]"
    assert "top-secret-value" not in event["stdout"]
    assert "top-secret-value" not in (tmp_path / "audit.jsonl").read_text(encoding="utf-8")


def test_executor_does_not_inherit_unapproved_environment_variables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOMECMD_TEST_SECRET", "must-not-leak")
    path = tmp_path / "commands.toml"
    path.write_text(
        '''\
[[commands]]
id = "test.environment"
summary = "Inspect one environment variable"
risk = "read"
argv = ["@python", "-c", "import os; print(os.getenv('HOMECMD_TEST_SECRET', 'missing'))"]
''',
        encoding="utf-8",
    )
    executor = CommandExecutor(
        CommandRegistry.from_paths([path]),
        PolicyEngine.read_only(),
        AuditLog(tmp_path / "audit.jsonl"),
    )

    result = executor.run("test.environment", {})

    assert result.stdout.strip() == "missing"


def test_executor_requires_durable_start_audit_before_execution(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist"
    commands = tmp_path / "commands.toml"
    commands.write_text(
        f'''\
[[commands]]
id = "test.side-effect"
summary = "Create a marker"
risk = "read"
argv = ["@python", "-c", "from pathlib import Path; Path(r'{marker.as_posix()}').write_text('ran')"]
''',
        encoding="utf-8",
    )

    class FailingAudit(AuditLog):
        def record_start(self, *args, **kwargs):
            raise OSError("audit unavailable")

    executor = CommandExecutor(
        CommandRegistry.from_paths([commands]),
        PolicyEngine.read_only(),
        FailingAudit(tmp_path / "audit.jsonl"),
    )

    with pytest.raises(OSError, match="audit unavailable"):
        executor.run("test.side-effect", {})

    assert not marker.exists()


def test_audit_records_start_before_completion(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    executor = CommandExecutor(make_registry(tmp_path), PolicyEngine.read_only(), audit)

    result = executor.run("test.echo", {"message": "hello"})
    events = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()]

    assert [event["event"] for event in events] == ["start", "complete"]
    assert audit.get(result.run_id)["event"] == "complete"
