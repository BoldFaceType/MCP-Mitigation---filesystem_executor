from pathlib import Path

import pytest

from homecmd.registry import CommandRegistry, DuplicateCommandError


REGISTRY_TOML = """
[[commands]]
id = "system.echo"
summary = "Echo one inert argument"
risk = "read"
argv = ["@python", "-c", "import sys; print(sys.argv[1])", "{message}"]
timeout_seconds = 5
max_output_chars = 1000

[[commands.arguments]]
name = "message"
type = "string"
required = true

[[commands]]
id = "system.python_version"
summary = "Show the Python version"
risk = "read"
argv = ["@python", "--version"]
"""


def write_registry(tmp_path: Path, content: str = REGISTRY_TOML) -> Path:
    path = tmp_path / "commands.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_registry_search_returns_compact_summaries(tmp_path: Path) -> None:
    registry = CommandRegistry.from_paths([write_registry(tmp_path)])

    results = registry.search("python version")

    assert [result.id for result in results] == ["system.python_version"]
    assert results[0].model_dump() == {
        "id": "system.python_version",
        "summary": "Show the Python version",
        "risk": "read",
        "args": [],
    }


def test_registry_returns_exact_command_card(tmp_path: Path) -> None:
    registry = CommandRegistry.from_paths([write_registry(tmp_path)])

    card = registry.get("system.echo")

    assert card.id == "system.echo"
    assert card.argv[-1] == "{message}"
    assert card.arguments[0].name == "message"
    assert card.arguments[0].required is True


def test_registry_rejects_duplicate_command_ids(tmp_path: Path) -> None:
    first = write_registry(tmp_path)
    second = tmp_path / "other.toml"
    second.write_text(REGISTRY_TOML, encoding="utf-8")

    with pytest.raises(DuplicateCommandError, match="system.echo"):
        CommandRegistry.from_paths([first, second])


def test_registry_rejects_undefined_argument_placeholder(tmp_path: Path) -> None:
    path = write_registry(tmp_path, '''\
[[commands]]
id = "unsafe.template"
summary = "Invalid template"
risk = "read"
argv = ["tool", "{undefined}"]
''')

    with pytest.raises(ValueError, match="undefined"):
        CommandRegistry.from_paths([path])


def test_registry_rejects_variable_executable(tmp_path: Path) -> None:
    path = write_registry(tmp_path, '''\
[[commands]]
id = "unsafe.executable"
summary = "Invalid executable"
risk = "read"
argv = ["{program}", "--version"]

[[commands.arguments]]
name = "program"
required = true
''')

    with pytest.raises(ValueError, match="executable"):
        CommandRegistry.from_paths([path])


def test_registry_rejects_argument_names_that_cannot_be_placeholders(tmp_path: Path) -> None:
    path = write_registry(tmp_path, '''\
[[commands]]
id = "unsafe.argument-name"
summary = "Invalid argument name"
risk = "read"
argv = ["tool", "{bad-name}"]

[[commands.arguments]]
name = "bad-name"
required = true
''')

    with pytest.raises(ValueError, match="name"):
        CommandRegistry.from_paths([path])


def test_registry_search_caps_results_for_progressive_disclosure(tmp_path: Path) -> None:
    commands = "\n".join(
        f'''\
[[commands]]
id = "test.command_{number:02d}"
summary = "Token bounded command {number}"
argv = ["tool", "--version"]
'''
        for number in range(25)
    )
    registry = CommandRegistry.from_paths([write_registry(tmp_path, commands)])

    results = registry.search("command")

    assert len(results) == 20
    assert results[0].id == "test.command_00"
    assert results[-1].id == "test.command_19"


def test_registry_rejects_shell_interpreter_cards(tmp_path: Path) -> None:
    path = write_registry(tmp_path, '''\
[[commands]]
id = "unsafe.shell"
summary = "Caller controlled shell source"
risk = "read"
argv = ["sh", "-c", "{code}"]

[[commands.arguments]]
name = "code"
required = true
''')

    with pytest.raises(ValueError, match="shell interpreters"):
        CommandRegistry.from_paths([path])
