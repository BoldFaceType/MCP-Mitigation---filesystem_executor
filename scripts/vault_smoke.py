"""Run packaged vault cards through the real homecmd CLI path."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


CONTENT = "---\ntitle: Homecmd Smoke\n---\n\nVault boundary verified."


def run_homecmd(env: dict[str, str], *arguments: str) -> dict:
    process = subprocess.run(
        [sys.executable, "-m", "homecmd.cli", *arguments],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"homecmd failed: {process.stdout}{process.stderr}")
    return json.loads(process.stdout)


def main() -> int:
    root = Path(__file__).parents[1]
    with tempfile.TemporaryDirectory(prefix="homecmd-vault-smoke-") as temp_dir:
        vault = Path(temp_dir) / "vault"
        vault.mkdir()
        audit = Path(temp_dir) / "audit.jsonl"
        env = os.environ.copy()
        env["HOMECMD_VAULT_ROOT"] = str(vault)
        env["HOMECMD_AUDIT_LOG"] = str(audit)
        env["HOMECMD_POLICY"] = str(root / "configs" / "policy.vault-write.toml")

        written = run_homecmd(
            env,
            "run",
            "filesystem.write",
            "path=03-Wiki/smoke.md",
            f"content={CONTENT}",
        )
        read = run_homecmd(env, "run", "filesystem.read", "path=03-Wiki/smoke.md")
        listing = run_homecmd(env, "run", "filesystem.list", "path=03-Wiki")

        if not written.get("ok") or read.get("stdout") != CONTENT:
            raise RuntimeError("vault write/read round trip failed")
        entries = json.loads(listing["stdout"])
        if [entry["path"] for entry in entries] != ["03-Wiki/smoke.md"]:
            raise RuntimeError(f"unexpected vault listing: {entries}")
        audit_text = audit.read_text(encoding="utf-8")
        if CONTENT in audit_text:
            raise RuntimeError("vault content persisted in audit")

    print(json.dumps({
        "write": True,
        "read": True,
        "list": True,
        "content_persisted_in_audit": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
