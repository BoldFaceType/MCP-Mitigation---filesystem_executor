from __future__ import annotations

from collections.abc import Iterable
import tomllib
from pathlib import Path

from .models import CommandCard, Risk


class PolicyDenied(PermissionError):
    pass


class PolicyEngine:
    def __init__(self, allowed_risks: Iterable[Risk]) -> None:
        self._allowed_risks = frozenset(allowed_risks)

    @classmethod
    def read_only(cls) -> "PolicyEngine":
        return cls(("read",))

    @classmethod
    def from_toml(cls, path: Path) -> "PolicyEngine":
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        allowed = data.get("allowed_risks", [])
        known = {"read", "write", "destructive", "secret", "network"}
        if not isinstance(allowed, list) or any(risk not in known for risk in allowed):
            raise ValueError("allowed_risks contains an invalid risk")
        return cls(allowed)

    def authorize(self, card: CommandCard) -> None:
        if card.risk not in self._allowed_risks:
            raise PolicyDenied(f"Policy denies {card.risk} command: {card.id}")
