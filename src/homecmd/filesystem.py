from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


class VaultPathError(ValueError):
    pass


def resolve_vault_path(root: Path, relative: str) -> Path:
    root = Path(root).expanduser().resolve()
    candidate_path = Path(relative)
    if candidate_path.is_absolute():
        raise VaultPathError("vault path must be relative")
    candidate = (root / candidate_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise VaultPathError("vault path escapes configured root") from exc
    return candidate


def read_vault_file(root: Path, relative: str, max_chars: int) -> str:
    target = resolve_vault_path(root, relative)
    if not target.is_file():
        raise VaultPathError("vault path is not a file")
    with target.open(encoding="utf-8") as stream:
        content = stream.read(max_chars + 1)
    if len(content) > max_chars:
        raise ValueError(f"file exceeds {max_chars} character limit")
    return content


def list_vault_path(root: Path, relative: str, max_entries: int) -> list[dict[str, object]]:
    root = Path(root).expanduser().resolve()
    target = resolve_vault_path(root, relative)
    if not target.is_dir():
        raise VaultPathError("vault path is not a directory")
    entries = sorted(target.iterdir(), key=lambda path: path.name.casefold())
    if len(entries) > max_entries:
        raise ValueError(f"directory exceeds {max_entries} entry limit")
    return [_entry(root, entry) for entry in entries]


def write_vault_file(root: Path, relative: str, content: str) -> None:
    target = resolve_vault_path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=".homecmd-", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _entry(root: Path, path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(root).as_posix(),
        "type": "directory" if path.is_dir() else "file",
        "size": path.stat().st_size if path.is_file() else None,
    }


def _root_from_environment() -> Path:
    configured = os.getenv("HOMECMD_VAULT_ROOT", "").strip()
    if not configured:
        raise VaultPathError("HOMECMD_VAULT_ROOT is required")
    root = Path(configured).expanduser().resolve()
    if not root.is_dir():
        raise VaultPathError("configured vault root is not a directory")
    return root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="homecmd-filesystem")
    commands = parser.add_subparsers(dest="operation", required=True)
    read = commands.add_parser("read")
    read.add_argument("path")
    listing = commands.add_parser("list")
    listing.add_argument("path")
    write = commands.add_parser("write")
    write.add_argument("path")
    write.add_argument("content")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = _root_from_environment()
        if args.operation == "read":
            print(read_vault_file(root, args.path, max_chars=12_000), end="")
        elif args.operation == "list":
            print(json.dumps(list_vault_path(root, args.path, max_entries=200), separators=(",", ":")))
        else:
            write_vault_file(root, args.path, args.content)
            print(json.dumps({"written": args.path}, separators=(",", ":")))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
