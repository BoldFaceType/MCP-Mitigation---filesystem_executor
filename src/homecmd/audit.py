from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from .models import RunResult


REDACTED = "[REDACTED]"


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = Lock()

    def record_start(
        self,
        run_id: str,
        command_id: str,
        args: dict[str, object],
        secret_names: set[str],
    ) -> dict[str, Any]:
        event = {
            "event": "start",
            "run_id": run_id,
            "command_id": command_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "args": {
                name: REDACTED if name in secret_names else value
                for name, value in args.items()
            },
        }
        self._append(event)
        return event

    def record(
        self,
        result: RunResult,
        args: dict[str, object],
        secret_names: set[str],
        sensitive_output: bool = False,
    ) -> dict[str, Any]:
        secret_values = _secret_values(args, secret_names)
        event = result.model_dump(mode="json")
        event["event"] = "complete"
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        event["args"] = {
            name: REDACTED if name in secret_names else value
            for name, value in args.items()
        }
        event["stdout"] = _redact(event["stdout"], secret_values)
        event["stderr"] = _redact(event["stderr"], secret_values)
        if sensitive_output:
            event["stdout"] = REDACTED
            event["stderr"] = REDACTED
        self._append(event)
        return event

    def record_worker(
        self,
        *,
        run_id: str,
        ok: bool,
        model: str | None,
        input_chars: int,
        output_chars: int,
        truncated: bool,
        error: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "event": "call_worker",
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ok": ok,
            "backend": "lmstudio",
            "model": model,
            "input_chars": input_chars,
            "output_chars": output_chars,
            "truncated": truncated,
            "error": error,
        }
        self._append(event)
        return event

    def _append(self, event: dict[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                self.path.touch(mode=0o600)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=True, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())

    def get(self, run_id: str) -> dict[str, Any]:
        if not self.path.exists():
            raise KeyError(run_id)
        matched: dict[str, Any] | None = None
        with self.path.open(encoding="utf-8") as stream:
            for line in stream:
                event = json.loads(line)
                if event.get("run_id") == run_id:
                    matched = event
        if matched is None:
            raise KeyError(run_id)
        return matched


def _secret_values(args: dict[str, object], secret_names: set[str]) -> tuple[str, ...]:
    return tuple(
        str(args[name])
        for name in secret_names
        if name in args and str(args[name])
    )


def _redact(text: str, secret_values: tuple[str, ...]) -> str:
    for value in secret_values:
        text = text.replace(value, REDACTED)
    return text
