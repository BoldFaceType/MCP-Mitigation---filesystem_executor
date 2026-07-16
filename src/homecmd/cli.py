from __future__ import annotations

import argparse
import json
import os
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any, TextIO

from .app import HomecmdService
from .audit import AuditLog
from .executor import CommandExecutor
from .policy import PolicyEngine
from .registry import CommandRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="homecmd", description="Policy-gated local command gateway.")
    commands = parser.add_subparsers(dest="operation", required=True)

    search = commands.add_parser("search", help="Find approved command cards.")
    search.add_argument("query", nargs="+")

    card = commands.add_parser("card", help="Show one approved command card.")
    card.add_argument("command_id")

    run = commands.add_parser("run", help="Run one approved command.")
    run.add_argument("command_id")
    run.add_argument("arguments", nargs="*")

    log = commands.add_parser("log", help="Read one redacted run record.")
    log.add_argument("run_id")

    serve = commands.add_parser("serve", help="Start the ACP server.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8000, type=int)
    return parser


def build_default_service(*, audit_path: Path | None = None) -> HomecmdService:
    configured = os.getenv("HOMECMD_COMMANDS")
    command_path = Path(configured) if configured else Path(str(files("homecmd") / "data" / "commands" / "core.toml"))
    active_audit_path = audit_path or Path(
        os.getenv("HOMECMD_AUDIT_LOG", Path.home() / ".homecmd" / "audit.jsonl")
    )
    policy_path = os.getenv("HOMECMD_POLICY")
    registry = CommandRegistry.from_paths([command_path])
    audit = AuditLog(active_audit_path)
    policy = PolicyEngine.from_toml(Path(policy_path)) if policy_path else PolicyEngine.read_only()
    executor = CommandExecutor(registry, policy, audit)
    return HomecmdService(registry, executor, audit)


def parse_key_values(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(value)
        key, raw = value.split("=", 1)
        if not key or key in parsed:
            raise ValueError(value)
        parsed[key] = raw
    return parsed


def emit(payload: object, stdout: TextIO) -> None:
    stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def execute_operation(service: HomecmdService, args: argparse.Namespace) -> object:
    if args.operation == "search":
        return service.search(" ".join(args.query))
    if args.operation == "card":
        return service.card(args.command_id)
    if args.operation == "run":
        return service.run(args.command_id, parse_key_values(args.arguments))
    return service.log(args.run_id)


def main(
    argv: list[str] | None = None,
    *,
    service: HomecmdService | None = None,
    stdout: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    args = build_parser().parse_args(argv)

    if args.operation == "serve":
        from .server import run_server

        return run_server(host=args.host, port=args.port)

    active_service = service or build_default_service()
    try:
        payload = execute_operation(active_service, args)
    except ValueError as exc:
        emit({"error": "invalid_argument", "message": str(exc)}, output)
        return 2
    except Exception as exc:
        emit({"error": type(exc).__name__, "message": str(exc)}, output)
        return 1

    emit(payload, output)
    if isinstance(payload, dict) and payload.get("ok") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
