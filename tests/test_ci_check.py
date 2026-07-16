import json
from pathlib import Path

from scripts.ci_check import check_agent_board, check_python_quality


def write_board(tmp_path: Path, events: list[dict]) -> Path:
    board = tmp_path / "AGENT_BOARD.jsonl"
    board.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )
    return board


def event(name: str, timestamp: str = "2026-07-05T12:00:00Z") -> dict:
    payload = {
        "ts": timestamp,
        "event": name,
        "agent": "test-agent",
        "slice": "test-slice",
    }
    if name in {"claim", "takeover"}:
        payload["lease_minutes"] = 15
    return payload


def test_agent_board_accepts_claim_start_handoff_release(tmp_path: Path) -> None:
    write_board(tmp_path, [
        event("claim"),
        event("start", "2026-07-05T12:00:01Z"),
        event("handoff", "2026-07-05T12:00:02Z"),
        event("release", "2026-07-05T12:00:03Z"),
    ])

    assert check_agent_board(tmp_path) == []


def test_agent_board_rejects_start_without_claim(tmp_path: Path) -> None:
    write_board(tmp_path, [event("start")])

    errors = check_agent_board(tmp_path)

    assert any("start requires" in error for error in errors)


def test_agent_board_rejects_takeover_before_stale_timeout(tmp_path: Path) -> None:
    takeover = event("takeover", "2026-07-05T12:05:00Z")
    takeover["agent"] = "other-agent"
    write_board(tmp_path, [event("claim"), event("start", "2026-07-05T12:00:01Z"), takeover])

    errors = check_agent_board(tmp_path)

    assert any("takeover requires a stale" in error for error in errors)


def test_agent_board_accepts_takeover_after_stale_timeout(tmp_path: Path) -> None:
    takeover = event("takeover", "2026-07-05T12:10:02Z")
    takeover["agent"] = "other-agent"
    write_board(tmp_path, [event("claim"), event("start", "2026-07-05T12:00:01Z"), takeover])

    assert check_agent_board(tmp_path) == []


def test_agent_board_rejects_event_from_non_owner(tmp_path: Path) -> None:
    heartbeat = event("heartbeat", "2026-07-05T12:01:00Z")
    heartbeat["agent"] = "other-agent"
    write_board(tmp_path, [event("claim"), event("start", "2026-07-05T12:00:01Z"), heartbeat])

    errors = check_agent_board(tmp_path)

    assert any("active owner" in error for error in errors)


def test_python_quality_rejects_complexity_over_ten(tmp_path: Path) -> None:
    source = tmp_path / "complex.py"
    source.write_text(
        "def too_complex(value):\n"
        + "".join(f"    if value == {number}:\n        return {number}\n" for number in range(10))
        + "    return value\n",
        encoding="utf-8",
    )

    errors = check_python_quality(tmp_path)

    assert any("complexity 11" in error for error in errors)
