"""Repository hygiene checks for MCP Mitigation.

This script intentionally uses only the Python standard library so repository
structure can be validated before package dependencies are installed.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re
import sys
from pathlib import Path


REQUIRED_PATHS = [
    Path("README.md"),
    Path("TASK_MANIFEST.md"),
    Path("AGENT_BOARD.jsonl"),
    Path("manifest_slices.md"),
    Path("pyproject.toml"),
    Path("src/homecmd/cli.py"),
    Path("src/homecmd/acp.py"),
    Path("src/homecmd/data/commands/core.toml"),
    Path("tests/test_acp.py"),
    Path("docs/architecture/mcp-mitigation-v0.4.0-canvas.md"),
]

CONFLICT_MARKER_RE = re.compile(r"^(<<<<<<<|=======|>>>>>>>)")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
BOARD_EVENTS = {
    "claim",
    "start",
    "heartbeat",
    "block",
    "handoff",
    "merge",
    "release",
    "takeover",
}
BOARD_TRANSITIONS = {
    "claim": ({None, "released"}, "claimed", "claim requires an unowned slice"),
    "start": ({"claimed"}, "started", "start requires a claim"),
    "heartbeat": ({"started"}, None, "heartbeat requires active work"),
    "block": ({"started"}, "blocked", "block requires active work"),
    "handoff": ({"started", "blocked"}, "handed_off", "handoff requires active or blocked work"),
    "merge": ({"handed_off"}, "merged", "merge requires a handoff"),
    "release": ({"started", "blocked", "handed_off", "merged"}, "released", "release requires owned work"),
}
LEASE_DURATION = timedelta(minutes=15)
STALE_TIMEOUT = timedelta(minutes=10)


@dataclass
class BoardState:
    owner: str
    status: str
    last_activity: datetime
    lease_end: datetime


def iter_text_files(root: Path) -> list[Path]:
    skip_dirs = {".git", ".venv", "venv", "__pycache__"}
    suffixes = {".md", ".py", ".yml", ".yaml", ".toml", ".json", ".txt"}
    files: list[Path] = []

    for path in root.rglob("*"):
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.is_file() and (path.suffix.lower() in suffixes or path.name in {"README"}):
            files.append(path)

    return files


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_required_paths(root: Path) -> list[str]:
    errors: list[str] = []
    for rel_path in REQUIRED_PATHS:
        if not (root / rel_path).is_file():
            errors.append(f"missing required file: {rel_path.as_posix()}")
    return errors


def check_conflict_markers(root: Path) -> list[str]:
    errors: list[str] = []
    for path in iter_text_files(root):
        for line_number, line in enumerate(read_text(path).splitlines(), start=1):
            if CONFLICT_MARKER_RE.match(line):
                errors.append(f"merge conflict marker found in {path.relative_to(root)}:{line_number}")
    return errors


def check_markdown_fences(root: Path) -> list[str]:
    errors: list[str] = []
    for path in root.rglob("*.md"):
        if ".git" in path.parts:
            continue
        fence_count = 0
        for line in read_text(path).splitlines():
            if line.lstrip().startswith("```"):
                fence_count += 1
        if fence_count % 2:
            errors.append(f"unbalanced markdown code fence in {path.relative_to(root)}")
    return errors


def is_external_link(target: str) -> bool:
    lowered = target.lower()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("mailto:")
        or lowered.startswith("#")
    )


def strip_anchor(target: str) -> str:
    return target.split("#", 1)[0]


def _check_markdown_target(root: Path, source: Path, raw_target: str) -> str | None:
    target = raw_target.strip()
    if not target or is_external_link(target):
        return None
    target = strip_anchor(target)
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if not target or "://" in target:
        return None
    resolved = (source.parent / target).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return f"markdown link escapes repo in {source.relative_to(root)}: {target}"
    if not resolved.exists():
        return f"broken local markdown link in {source.relative_to(root)}: {target}"
    return None


def check_local_markdown_links(root: Path) -> list[str]:
    errors: list[str] = []
    for path in root.rglob("*.md"):
        if ".git" in path.parts:
            continue
        text = read_text(path)
        for match in MARKDOWN_LINK.finditer(text):
            error = _check_markdown_target(root, path, match.group(1))
            if error:
                errors.append(error)
    return errors


def check_manifest_slices(root: Path) -> list[str]:
    manifest = root / "manifest_slices.md"
    if not manifest.is_file():
        return ["missing manifest_slices.md"]

    text = read_text(manifest)
    required_terms = [
        "acp_homecmd",
        "contracts_registry",
        "policy_executor",
        "cli_service",
        "acp_protocol",
        "docs_adapter",
        "Merge Gate",
    ]
    return [f"manifest_slices.md missing required term: {term}" for term in required_terms if term not in text]


def check_removed_legacy_runtime(root: Path) -> list[str]:
    forbidden = [
        Path("src/main.py"),
        Path("src/executor.py"),
        Path("open-webui-tool.py"),
        Path("workspace-tools.py"),
        Path("mqtt-tools.py"),
    ]
    return [f"legacy runtime must remain removed: {path.as_posix()}" for path in forbidden if (root / path).exists()]


def check_homecmd_security_shape(root: Path) -> list[str]:
    errors: list[str] = []
    source_root = root / "src" / "homecmd"
    for path in source_root.rglob("*.py"):
        text = read_text(path)
        if "shell=True" in text or "bash -c" in text:
            errors.append(f"unsafe shell execution found in {path.relative_to(root)}")
    return errors


def _parse_board_event(line: str, line_number: int) -> tuple[dict[str, object] | None, list[str]]:
    try:
        event = json.loads(line)
    except json.JSONDecodeError as exc:
        return None, [f"invalid AGENT_BOARD.jsonl JSON at line {line_number}: {exc.msg}"]
    if not isinstance(event, dict):
        return None, [f"AGENT_BOARD.jsonl line {line_number} must be an object"]
    missing = [name for name in ("ts", "event", "agent", "slice") if not event.get(name)]
    errors = [f"AGENT_BOARD.jsonl line {line_number} missing field: {name}" for name in missing]
    if event.get("event") not in BOARD_EVENTS:
        errors.append(f"AGENT_BOARD.jsonl line {line_number} has unknown event: {event.get('event')}")
    if event.get("event") in {"claim", "takeover"} and event.get("lease_minutes") != 15:
        errors.append(f"AGENT_BOARD.jsonl line {line_number} must use a 15-minute lease")
    try:
        datetime.fromisoformat(str(event.get("ts", "")).replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"AGENT_BOARD.jsonl line {line_number} has invalid timestamp")
    return event, errors


def _next_board_state(current: str | None, event: str) -> tuple[str | None, str | None]:
    transition = BOARD_TRANSITIONS.get(event)
    if transition is None:
        return current, None
    allowed, target, error = transition
    if current not in allowed:
        return current, error
    return target or current, None


def _new_board_state(event: dict[str, object], timestamp: datetime, status: str) -> BoardState:
    return BoardState(
        owner=str(event["agent"]),
        status=status,
        last_activity=timestamp,
        lease_end=timestamp + LEASE_DURATION,
    )


def _claim_or_takeover(
    state: BoardState | None,
    event: dict[str, object],
    timestamp: datetime,
) -> tuple[BoardState | None, str | None]:
    kind = str(event["event"])
    if kind == "claim":
        if state is None or state.status == "released":
            return _new_board_state(event, timestamp, "claimed"), None
        return state, "claim conflicts with the earliest active lease"
    stale = state is not None and (
        timestamp - state.last_activity > STALE_TIMEOUT or timestamp >= state.lease_end
    )
    if not stale:
        return state, "takeover requires a stale or expired lease"
    return _new_board_state(event, timestamp, "started"), None


def _apply_owned_event(
    state: BoardState | None,
    event: dict[str, object],
    timestamp: datetime,
) -> tuple[BoardState | None, str | None]:
    kind = str(event["event"])
    if state is None:
        return None, f"{kind} requires a claim"
    if str(event["agent"]) != state.owner:
        return state, f"{kind} must be emitted by the active owner"
    if timestamp - state.last_activity > STALE_TIMEOUT and kind != "release":
        return state, f"{kind} follows a stale lease; takeover is required"
    next_status, error = _next_board_state(state.status, kind)
    if error:
        return state, error
    state.status = next_status or state.status
    state.last_activity = timestamp
    if kind == "heartbeat":
        state.lease_end = timestamp + LEASE_DURATION
    return state, None


def _apply_board_event(
    state: BoardState | None,
    event: dict[str, object],
    timestamp: datetime,
) -> tuple[BoardState | None, str | None]:
    kind = str(event["event"])
    if kind in {"claim", "takeover"}:
        return _claim_or_takeover(state, event, timestamp)
    return _apply_owned_event(state, event, timestamp)


def check_agent_board(root: Path) -> list[str]:
    path = root / "AGENT_BOARD.jsonl"
    if not path.is_file():
        return ["missing AGENT_BOARD.jsonl"]
    errors: list[str] = []
    states: dict[str, BoardState] = {}
    previous_timestamp: datetime | None = None
    for line_number, line in enumerate(read_text(path).splitlines(), start=1):
        event, parse_errors = _parse_board_event(line, line_number)
        errors.extend(parse_errors)
        if event is None or parse_errors:
            continue
        timestamp = datetime.fromisoformat(str(event["ts"]).replace("Z", "+00:00"))
        if previous_timestamp and timestamp < previous_timestamp:
            errors.append(f"AGENT_BOARD.jsonl line {line_number} timestamp is out of order")
        previous_timestamp = timestamp
        slice_name = str(event["slice"])
        next_state, transition_error = _apply_board_event(states.get(slice_name), event, timestamp)
        if transition_error:
            errors.append(f"AGENT_BOARD.jsonl line {line_number}: {transition_error}")
        if next_state:
            states[slice_name] = next_state
    return errors


def _cyclomatic_complexity(function: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    complexity = 1
    for node in ast.walk(function):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.comprehension)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += max(0, len(node.values) - 1)
        elif isinstance(node, ast.Try):
            complexity += len(node.handlers) + bool(node.orelse) + bool(node.finalbody)
        elif isinstance(node, ast.Match):
            complexity += len(node.cases)
    return complexity


def check_python_quality(root: Path) -> list[str]:
    errors: list[str] = []
    for path in root.rglob("*.py"):
        if any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts):
            continue
        try:
            tree = ast.parse(read_text(path), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"Python syntax error in {path.relative_to(root)}:{exc.lineno}: {exc.msg}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = _cyclomatic_complexity(node)
                if complexity > 10:
                    errors.append(
                        f"Python complexity {complexity} exceeds 10 in "
                        f"{path.relative_to(root)}:{node.lineno} ({node.name})"
                    )
    return errors


def run(root: Path) -> list[str]:
    checks = [
        check_required_paths,
        check_conflict_markers,
        check_markdown_fences,
        check_local_markdown_links,
        check_manifest_slices,
        check_removed_legacy_runtime,
        check_homecmd_security_shape,
        check_agent_board,
        check_python_quality,
    ]
    errors: list[str] = []
    for check in checks:
        errors.extend(check(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repository hygiene checks.")
    parser.add_argument("--root", default=".", help="Repository root to check.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors = run(root)
    if errors:
        print("CI check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("CI check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
