"""Repository hygiene checks for MCP Mitigation.

This script intentionally uses only the Python standard library so it can run
locally and in GitHub Actions before the project has package dependencies.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_PATHS = [
    Path("README.md"),
    Path("manifest_slices.md"),
    Path("docs/architecture/mcp-mitigation-v0.3.0-canvas.md"),
]

CONFLICT_MARKER_RE = re.compile(r"^(<<<<<<<|=======|>>>>>>>)")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


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


def check_local_markdown_links(root: Path) -> list[str]:
    errors: list[str] = []
    for path in root.rglob("*.md"):
        if ".git" in path.parts:
            continue
        text = read_text(path)
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group(1).strip()
            if not target or is_external_link(target):
                continue
            target = strip_anchor(target)
            if not target:
                continue
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            if "://" in target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                errors.append(f"markdown link escapes repo in {path.relative_to(root)}: {target}")
                continue
            if not resolved.exists():
                errors.append(f"broken local markdown link in {path.relative_to(root)}: {target}")
    return errors


def check_manifest_slices(root: Path) -> list[str]:
    manifest = root / "manifest_slices.md"
    if not manifest.is_file():
        return ["missing manifest_slices.md"]

    text = read_text(manifest)
    required_terms = [
        "bridge_mcp",
        "registry_policy",
        "executor_adapters",
        "api_service",
        "docs_install",
        "ci_cd",
        "Merge Gate",
    ]
    return [f"manifest_slices.md missing required term: {term}" for term in required_terms if term not in text]


def run(root: Path) -> list[str]:
    checks = [
        check_required_paths,
        check_conflict_markers,
        check_markdown_fences,
        check_local_markdown_links,
        check_manifest_slices,
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
