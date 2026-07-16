# MCP Mitigation Slice Manifest

Version: 0.2.0
Date: 2026-07-16
Status: WIP Handoff / Adapter Execution Blocked

## Integration Slice

| Slice | Branch | Worktree | Responsibility |
|---|---|---|---|
| `acp_homecmd` | `feature/acp-homecmd` | `C:/Dev/projects/mcp-acp-homecmd` | ACP-first gateway, direct CLI, registry, policy, executor, audit, adapter docs, and CI |

## Component Ownership

### `contracts_registry`

Owned paths:

- `src/homecmd/models.py`
- `src/homecmd/registry.py`
- `src/homecmd/data/commands/`
- `tests/test_registry.py`

Contract:

- Command IDs are unique.
- Executables are fixed by operator-owned cards.
- Search returns compact summaries.
- Invalid templates fail at startup.

### `policy_executor`

Owned paths:

- `src/homecmd/policy.py`
- `src/homecmd/executor.py`
- `src/homecmd/audit.py`
- `configs/policy.*.toml`
- `tests/test_policy_executor.py`

Contract:

- Read-only policy is the default.
- Commands execute with `shell=False` and no stdin.
- Unknown commands and arguments fail closed.
- Outputs are bounded and secret values are redacted before persistence.

### `cli_service`

Owned paths:

- `src/homecmd/app.py`
- `src/homecmd/cli.py`
- `tests/test_cli.py`

Contract:

- `search`, `card`, `run`, and `log` call one shared service.
- CLI JSON output is stable and machine-readable.

### `acp_protocol`

Owned paths:

- `src/homecmd/acp.py`
- `src/homecmd/server.py`
- `tests/test_acp.py`

Contract:

- ACP clients use agent discovery and synchronous runs.
- MCP clients terminate at the external `acp-mcp` adapter.
- Non-loopback binding requires authentication and TLS termination.
- No legacy raw execution routes are present.

### `docs_adapter`

Owned paths:

- `README.md`
- `OPERATIONS.md`
- `MCP_ACTIVATION_DISCOVERY.md`
- `configs/mcp-clients/`
- `Dockerfile`
- `CHANGELOG.md`

### `ci_governance`

Owned paths:

- `.github/`
- `scripts/ci_check.py`
- `TASK_MANIFEST.md`
- `AGENT_BOARD.jsonl`
- `manifest_slices.md`
- `docs/superpowers/`

## Cross-Slice Rules

- One owner edits a component path at a time.
- Do not restore the removed raw `/execute`, filesystem, MQTT, Open-WebUI, or embedded MCP-worker surfaces.
- Dependencies must be declared in `pyproject.toml`.
- The frozen ACP compatibility layer must remain isolated from registry, policy, and execution internals.
- Broad formatting changes across component boundaries are not allowed.

## Required Event Lifecycle

Multi-agent work appends events to `AGENT_BOARD.jsonl` in this order:

1. `claim`
2. `start`
3. `heartbeat` every five minutes
4. `block` when blocked
5. `handoff` when verified
6. `merge` after integration
7. `release` when ownership ends

## Merge Gate

- `git status --short` shows only intentional changes.
- `python -m pytest` passes.
- `python scripts/ci_check.py` passes.
- CLI and ACP smoke flows pass.
- Changes remain within the task manifest scope.
- Remaining risks are documented.
