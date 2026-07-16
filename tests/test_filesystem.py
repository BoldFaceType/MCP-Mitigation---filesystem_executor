import os
from pathlib import Path
import subprocess

import pytest

from homecmd.filesystem import (
    VaultPathError,
    list_vault_path,
    read_vault_file,
    resolve_vault_path,
    write_vault_file,
)
from homecmd.cli import build_default_service
from homecmd.policy import PolicyDenied


def test_vault_read_list_write_stays_under_root(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "01-Knowledge").mkdir()
    (root / "01-Knowledge" / "existing.md").write_text("existing", encoding="utf-8")

    write_vault_file(root, "03-Wiki/new-note.md", "new content")

    assert read_vault_file(root, "03-Wiki/new-note.md", max_chars=100) == "new content"
    entries = list_vault_path(root, "03-Wiki", max_entries=10)
    assert entries == [{"path": "03-Wiki/new-note.md", "type": "file", "size": 11}]


@pytest.mark.parametrize("path", ["../outside.md", "C:/outside.md", "/outside.md"])
def test_vault_rejects_paths_outside_root(tmp_path: Path, path: str) -> None:
    root = tmp_path / "vault"
    root.mkdir()

    with pytest.raises(VaultPathError):
        resolve_vault_path(root, path)


def test_vault_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    link = root / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            pytest.skip("symlinks are unavailable for this user")
        created = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        if created.returncode != 0:
            pytest.skip("symlinks and junctions are unavailable for this user")

    try:
        with pytest.raises(VaultPathError):
            resolve_vault_path(root, "linked/secret.md")
    finally:
        if os.name == "nt" and link.exists():
            link.rmdir()


def test_vault_read_enforces_character_cap(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "large.md").write_text("x" * 11, encoding="utf-8")

    with pytest.raises(ValueError, match="character limit"):
        read_vault_file(root, "large.md", max_chars=10)


def test_packaged_filesystem_cards_share_policy_and_redacted_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "note.md").write_text("private note", encoding="utf-8")
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("HOMECMD_VAULT_ROOT", str(root))
    monkeypatch.setenv("HOMECMD_AUDIT_LOG", str(audit_path))

    read_only = build_default_service()
    read_result = read_only.run("filesystem.read", {"path": "note.md"})

    assert read_result["ok"] is True
    assert read_result["stdout"] == "private note"
    assert "private note" not in audit_path.read_text(encoding="utf-8")
    with pytest.raises(PolicyDenied):
        read_only.run("filesystem.write", {"path": "new.md", "content": "---\ntitle: New\n---"})

    policy = Path(__file__).parents[1] / "configs" / "policy.vault-write.toml"
    monkeypatch.setenv("HOMECMD_POLICY", str(policy))
    writable = build_default_service()
    write_result = writable.run(
        "filesystem.write",
        {"path": "new.md", "content": "---\ntitle: New\n---"},
    )

    assert write_result["ok"] is True
    assert (root / "new.md").read_text(encoding="utf-8") == "---\ntitle: New\n---"
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "title: New" not in audit_text
    assert "[REDACTED]" in audit_text
