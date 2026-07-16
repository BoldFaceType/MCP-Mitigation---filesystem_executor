# ACP-First Homecmd Task Manifest

Version: 1.0.0
Date: 2026-07-16
Branch: `feature/acp-homecmd`
Worktree: `C:/Dev/projects/mcp-acp-homecmd`
Owner: `codex-primary`
Status: WIP publication; live MCP execution blocked

## Objective

Implement ACP as the primary network protocol for `homecmd-agent`, preserve a direct `homecmd` CLI, and document the existing ACP-MCP adapter as the compatibility path for MCP clients.

## Required Runtime Paths

```text
Human CLI   -> homecmd CLI       -> registry -> policy -> executor
ACP clients -> homecmd ACP agent -> registry -> policy -> executor
MCP clients -> ACP-MCP adapter   -> ACP agent -> registry -> policy -> executor
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

## Security Invariants

- The executor accepts only registered command IDs.
- Command arguments are validated and rendered without a shell.
- Shell interpreters are invalid command-card executables.
- Unknown arguments and unknown commands fail closed.
- Destructive, secret, and network commands are denied unless policy explicitly permits them.
- Local service binds to loopback by default.
- Non-loopback service startup requires an authentication token.
- Non-loopback service startup requires asserted TLS termination.
- Audit records redact configured secret field names.
- ACP and CLI call the same application service; neither bypasses policy.
- The MCP adapter terminates at ACP and receives no direct executor access.
- Search is capped at 20 summaries and ACP run previews at 4,000 characters.

## Work Slices

| Slice | Owned Files | Verification |
|---|---|---|
| contracts-registry | `src/homecmd/models.py`, `src/homecmd/registry.py`, `commands/` | registry tests |
| policy-executor | `src/homecmd/policy.py`, `src/homecmd/executor.py`, `src/homecmd/audit.py` | policy/executor tests |
| cli-service | `src/homecmd/cli.py`, `src/homecmd/app.py` | CLI tests |
| acp-protocol | `src/homecmd/acp.py`, ACP route tests | protocol tests |
| docs-adapter | README, operations, ACP-MCP adapter config | CI link and command checks |

## Test Commands

```powershell
python -m pytest
python scripts\ci_check.py
python -m py_compile src\homecmd\*.py
homecmd --help
homecmd search status
```

## Completion Gate

- All deliverables have direct current-state evidence.
- Full test suite passes from a clean checkout.
- Repository hygiene check passes.
- CLI search, card, run, and log flows pass.
- ACP discovery and run flows pass.
- ACP-MCP adapter setup is executable and documented against the ACP endpoint.
- No user or unrelated work is overwritten.

## Current Verification Status

- T1-T5, T7-T9, and T11 have local implementation and passing test evidence.
- T6 is configuration-complete but not execution-verified.
- T10 is blocked: the pinned adapter exposes `run_agent`, but live
  `tools/call` receives `400 Invalid ACP run request` from `homecmd-agent`.
- Previous LM Studio worker, Obsidian/filesystem, and MQTT outcomes are not yet
  represented by bounded command cards.
- This branch may be reviewed as a security-focused architecture preview; it
  must not be labeled a parity or production release.
