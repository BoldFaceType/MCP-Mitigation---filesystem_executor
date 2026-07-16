from __future__ import annotations

import tomllib
from pathlib import Path

from .models import CommandCard, CommandSummary


MAX_SEARCH_RESULTS = 20


class DuplicateCommandError(ValueError):
    pass


class CommandNotFoundError(KeyError):
    pass


class CommandRegistry:
    def __init__(self, cards: dict[str, CommandCard]) -> None:
        self._cards = dict(cards)

    @classmethod
    def from_paths(cls, paths: list[Path]) -> "CommandRegistry":
        cards: dict[str, CommandCard] = {}
        for path in paths:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            for raw_card in data.get("commands", []):
                card = CommandCard.model_validate(raw_card)
                if card.id in cards:
                    raise DuplicateCommandError(f"Duplicate command ID: {card.id}")
                cards[card.id] = card
        return cls(cards)

    def get(self, command_id: str) -> CommandCard:
        try:
            return self._cards[command_id]
        except KeyError as exc:
            raise CommandNotFoundError(command_id) from exc

    def search(self, query: str) -> list[CommandSummary]:
        terms = [term.lower() for term in query.split() if term.strip()]
        results: list[CommandSummary] = []
        for card in self._cards.values():
            haystack = f"{card.id} {card.summary}".lower()
            if all(term in haystack for term in terms):
                results.append(CommandSummary(
                    id=card.id,
                    summary=card.summary,
                    risk=card.risk,
                    args=[argument.name for argument in card.arguments],
                ))
        return sorted(results, key=lambda result: result.id)[:MAX_SEARCH_RESULTS]
