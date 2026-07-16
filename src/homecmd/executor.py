from __future__ import annotations

import re
import os
import subprocess
import sys
import tempfile
from typing import Any
from uuid import uuid4

from .audit import AuditLog
from .models import ArgumentSpec, CommandCard, RunResult
from .policy import PolicyEngine
from .registry import CommandRegistry


_PLACEHOLDER = re.compile(r"^\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_ALLOWED_ENVIRONMENT = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG")


class ArgumentValidationError(ValueError):
    pass


class CommandExecutor:
    def __init__(
        self,
        registry: CommandRegistry,
        policy: PolicyEngine,
        audit: AuditLog,
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._audit = audit

    def run(self, command_id: str, args: dict[str, Any]) -> RunResult:
        card = self._registry.get(command_id)
        self._policy.authorize(card)
        validated = _validate_arguments(card, args)
        argv = _build_argv(card, validated)
        run_id = str(uuid4())
        secret_names = {spec.name for spec in card.arguments if spec.secret}
        self._audit.record_start(run_id, card.id, validated, secret_names)
        result = _execute(run_id, card, argv)
        self._audit.record(result, validated, secret_names)
        return result


def _validate_arguments(card: CommandCard, args: dict[str, Any]) -> dict[str, str]:
    specs = {spec.name: spec for spec in card.arguments}
    unknown = sorted(set(args) - set(specs))
    if unknown:
        raise ArgumentValidationError(f"unknown arguments: {', '.join(unknown)}")
    missing = sorted(spec.name for spec in card.arguments if spec.required and spec.name not in args)
    if missing:
        raise ArgumentValidationError(f"missing arguments: {', '.join(missing)}")
    return {name: _validate_value(specs[name], value) for name, value in args.items()}


def _validate_value(spec: ArgumentSpec, value: Any) -> str:
    rendered = _render_value(spec, value)
    if rendered.startswith("-"):
        raise ArgumentValidationError(f"option-like argument rejected: {spec.name}")
    if "\x00" in rendered:
        raise ArgumentValidationError(f"invalid argument: {spec.name}")
    if spec.choices and rendered not in spec.choices:
        raise ArgumentValidationError(f"invalid choice for argument: {spec.name}")
    return rendered


def _render_value(spec: ArgumentSpec, value: Any) -> str:
    if spec.type in {"string", "path"}:
        if not isinstance(value, str):
            raise ArgumentValidationError(f"invalid {spec.type} argument: {spec.name}")
        return value
    if spec.type == "integer":
        if isinstance(value, bool):
            raise ArgumentValidationError(f"invalid integer argument: {spec.name}")
        try:
            return str(int(value))
        except (TypeError, ValueError) as exc:
            raise ArgumentValidationError(f"invalid integer argument: {spec.name}") from exc
    return _render_boolean(spec, value)


def _render_boolean(spec: ArgumentSpec, value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower()
    raise ArgumentValidationError(f"invalid boolean argument: {spec.name}")


def _build_argv(card: CommandCard, args: dict[str, str]) -> list[str]:
    argv: list[str] = []
    for token in card.argv:
        match = _PLACEHOLDER.fullmatch(token)
        if match:
            name = match.group(1)
            if name not in args:
                raise ArgumentValidationError(f"missing argument for placeholder: {name}")
            argv.append(args[name])
        else:
            argv.append(sys.executable if token == "@python" else token)
    return argv


def _execute(run_id: str, card: CommandCard, argv: list[str]) -> RunResult:
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            argv,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
            cwd=card.working_directory,
            env={name: os.environ[name] for name in _ALLOWED_ENVIRONMENT if name in os.environ},
        )
        timed_out = False
        try:
            process.wait(timeout=card.timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            timed_out = True
        stdout, stdout_cut = _read_bounded(stdout_file, card.max_output_chars)
        stderr, stderr_cut = _read_bounded(stderr_file, card.max_output_chars)
    if timed_out:
        return _timeout_result(run_id, card, stdout, stderr, stdout_cut or stderr_cut)
    return RunResult(
        run_id=run_id,
        command_id=card.id,
        ok=process.returncode == 0,
        exit_code=process.returncode,
        stdout=stdout,
        stderr=stderr,
        truncated=stdout_cut or stderr_cut,
    )


def _timeout_result(
    run_id: str,
    card: CommandCard,
    stdout: str,
    stderr: str,
    truncated: bool,
) -> RunResult:
    return RunResult(
        run_id=run_id,
        command_id=card.id,
        ok=False,
        exit_code=None,
        stdout=stdout,
        stderr=stderr,
        truncated=truncated,
        error="timeout",
    )


def _read_bounded(stream, limit: int) -> tuple[str, bool]:
    stream.seek(0)
    value = stream.read((limit * 4) + 5)
    text = value.decode(errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    return text[:limit], len(text) > limit or len(value) > (limit * 4) + 4
