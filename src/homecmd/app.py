from __future__ import annotations

from typing import Any

from .audit import AuditLog
from .executor import CommandExecutor
from .registry import CommandRegistry


class HomecmdService:
    def __init__(
        self,
        registry: CommandRegistry,
        executor: CommandExecutor,
        audit: AuditLog,
    ) -> None:
        self.registry = registry
        self.executor = executor
        self.audit = audit

    def search(self, query: str) -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in self.registry.search(query)]

    def card(self, command_id: str) -> dict[str, Any]:
        return self.registry.get(command_id).model_dump(mode="json")

    def run(self, command_id: str, args: dict[str, Any]) -> dict[str, Any]:
        return self.executor.run(command_id, args).model_dump(mode="json")

    def log(self, run_id: str) -> dict[str, Any]:
        return self.audit.get(run_id)
