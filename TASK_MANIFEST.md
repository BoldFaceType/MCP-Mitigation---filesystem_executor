# ACP-First Homecmd Task Manifest

Version: 1.0.0
Date: 2026-07-16
Branch: `feature/acp-homecmd`
Worktree: `C:/Dev/projects/mcp-acp-homecmd`
Owner: `codex-primary`
Status: RepoReady; approved use-case parity verified

## Objective

Implement ACP as the primary network protocol for `homecmd-agent`, preserve a direct `homecmd` CLI, and document the existing ACP-MCP adapter as the compatibility path for MCP clients.
Restore the separately bounded LM Studio worker plane and root-scoped Obsidian
filesystem outcomes without restoring raw execution endpoints.

## Required Runtime Paths

```text
Human CLI   -> homecmd CLI       -> registry -> policy -> executor
ACP clients -> homecmd ACP agent -> registry -> policy -> executor
MCP clients -> ACP-MCP adapter   -> ACP agent -> registry -> policy -> executor
Worker MCP  -> call_worker only  -> bounded local LM Studio client
```

## Deliverables

| ID | Deliverable | Evidence |
|---|---|---|
| T1 | Installable Python package and `homecmd` CLI | `pyproject.toml`; CLI tests |
| T2 | Compact command-card registry with `search` and `card` | registry module and tests |
| T3 | Policy-gated executor with no arbitrary shell passthrough | policy/executor modules and denial tests |
| T4 | Persistent redacted run log exposed through `homecmd log` | audit module and tests |
| T5 | ACP server as primary HTTP protocol | ACP endpoint tests and agent manifest |
| T6 | MCP compatibility through the existing ACP-MCP adapter | adapter configuration and documented smoke command |
| T7 | Safe starter command cards | `commands/core.yaml` or equivalent data file |
| T8 | Installation, configuration, and maintenance docs | README and operations guide |
| T9 | CI that runs unit and repository checks | workflow and local verification output |
| T10 | Repeatable live ACP-MCP compatibility check | `scripts/adapter_smoke.py`; adapter smoke output |
| T11 | Dated RepoReady architecture baseline | `docs/architecture/mcp-mitigation-v0.4.0-canvas.md` |
| T12 | Bounded native MCP `call_worker` for LM Studio | worker module, tests, live smoke |
| T13 | Vault-root read/list/write cards for Obsidian | filesystem module, policy, tests, live smoke |

## Security Invariants

- The executor accepts only registered command IDs.
- Command arguments are validated and rendered without a shell.
- Shell interpreters are invalid command-card executables.
- Caller-controlled interpreter source is invalid even with `shell=False`.
- Unknown arguments and unknown commands fail closed.
- Destructive, secret, and network commands are denied unless policy explicitly permits them.
- Local service binds to loopback by default.
- Non-loopback service startup requires an authentication token.
- Non-loopback service startup requires asserted TLS termination.
- Audit records redact configured secret field names.
- ACP and CLI call the same application service; neither bypasses policy.
- The MCP adapter terminates at ACP and receives no direct executor access.
- The native worker endpoint exposes exactly `call_worker` and has no executor access.
- Vault paths must resolve beneath `HOMECMD_VAULT_ROOT`.
- Vault content and worker prompts/responses are not persisted in audit output.
- Search is capped at 20 summaries and ACP run previews at 4,000 characters.

## Work Slices

| Slice | Owned Files | Verification |
|---|---|---|
| contracts-registry | `src/homecmd/models.py`, `src/homecmd/registry.py`, `commands/` | registry tests |
| policy-executor | `src/homecmd/policy.py`, `src/homecmd/executor.py`, `src/homecmd/audit.py` | policy/executor tests |
| cli-service | `src/homecmd/cli.py`, `src/homecmd/app.py` | CLI tests |
| acp-protocol | `src/homecmd/acp.py`, ACP route tests | protocol tests |
| bounded-worker | `src/homecmd/worker.py`, worker smoke | worker tests and live LM Studio call |
| vault-filesystem | `src/homecmd/filesystem.py`, filesystem cards | traversal and CLI smoke tests |
| docs-adapter | README, operations, ACP-MCP adapter config | CI link and command checks |

## Test Commands

```powershell
python -m pytest
python scripts\ci_check.py
python -m py_compile src\homecmd\*.py
homecmd --help
homecmd search status
python scripts\adapter_smoke.py
python scripts\worker_smoke.py
python scripts\vault_smoke.py
```

## Completion Gate

- All deliverables have direct current-state evidence.
- Full test suite passes from a clean checkout.
- Repository hygiene check passes.
- CLI search, card, run, and log flows pass.
- ACP discovery and run flows pass.
- ACP-MCP adapter setup is executable and documented against the ACP endpoint.
- Native worker MCP lists only `call_worker` and completes a live LM Studio call.
- Vault cards complete read/list/write under the configured root.
- No user or unrelated work is overwritten.

## Current Verification Status

- T1-T13 have implementation and current test or live-smoke evidence.
- The pinned adapter completes MCP `tools/call` through ACP.
- Native `/mcp` discovery exposes only `call_worker`; live LM Studio output is verified.
- Vault write/read/list completes through the real CLI with audit redaction.
- Git status/diff are fixed read-only cards. Docker remains separate; MQTT and
  Ollama are omitted because no installed CLI or approved current use case
  justifies their dependency or attack surface.
