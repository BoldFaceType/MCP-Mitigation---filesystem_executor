# MCP Mitigation Slice Manifest

Version: 0.1.0
Date: 2026-05-09
Status: Active

## Purpose

This manifest defines the planned vertical slices, ownership boundaries, branch names, and worktree names for parallel development.

Work should not begin in a slice until the slice has an active branch or worktree. A slice owner must avoid editing files owned by another slice unless the change is explicitly coordinated.

## Branch and Worktree Plan

| Slice | Branch | Worktree | Primary Responsibility |
|---|---|---|---|
| `bridge_mcp` | `feature/mcp-bridge` | `../mcp-bridge` | Compact MCP protocol bridge and MCP tool surface |
| `registry_policy` | `feature/registry-policy` | `../mcp-registry` | Command cards, registry search, schemas, and policy validation |
| `executor_adapters` | `feature/executor-adapters` | `../mcp-executor` | Safe command execution substrate and service adapters |
| `api_service` | `feature/api-service` | `../mcp-service` | Local/LAN API service, auth, progress, and cancellation endpoints |
| `docs_install` | `feature/install-docs` | `../mcp-docs` | Installation, configuration, operations, examples, and release notes |
| `ci_cd` | `feature/ci-cd` | `../mcp-ci` | GitHub Actions, local checks, workflow policy, and repository hygiene |

## Owned Paths

### `bridge_mcp`

Owned paths:

- `src/mcp_mitigation/bridge_mcp/`
- `tests/bridge_mcp/`
- `docs/architecture/*mcp*bridge*.md`

Expected checks:

- MCP bridge exposes only compact gateway tools.
- Tool schemas stay small and stable.
- Bridge calls the gateway instead of executing commands directly.

### `registry_policy`

Owned paths:

- `src/mcp_mitigation/registry/`
- `src/mcp_mitigation/policy/`
- `commands/`
- `configs/policy*.yaml`
- `tests/registry/`
- `tests/policy/`

Expected checks:

- Command cards validate against schema.
- Risk policies deny unsafe defaults.
- Registry search returns compact results.

### `executor_adapters`

Owned paths:

- `src/mcp_mitigation/executor/`
- `src/mcp_mitigation/adapters/`
- `tests/executor/`
- `tests/adapters/`

Expected checks:

- No arbitrary shell passthrough.
- Commands run non-interactively with timeout and output caps.
- Adapter outputs are structured and redacted before returning.

### `api_service`

Owned paths:

- `src/mcp_mitigation/service/`
- `configs/homecmd.yaml`
- `configs/policy.local.yaml`
- `configs/policy.lan.yaml`
- `tests/service/`

Expected checks:

- Local profile binds to loopback by default.
- LAN profile requires auth.
- Run, log, progress, and cancel endpoints are covered.

### `docs_install`

Owned paths:

- `README.md`
- `CHANGELOG.md`
- `docs/`
- `.env.example`
- `examples/`

Expected checks:

- Quickstart remains accurate.
- Install instructions do not assume unpublished packages.
- Operations docs include local and LAN safety guidance.

### `ci_cd`

Owned paths:

- `.github/`
- `scripts/`
- `manifest_slices.md`
- `tests/ci/`

Expected checks:

- CI uses no external services for baseline validation.
- Required docs and manifests exist.
- Markdown, conflict-marker, and repository hygiene checks run on every push and PR.

## Cross-Slice Rules

- Shared root files require coordination when more than one slice is active.
- Do not move or rename another slice's owned files without updating this manifest in the same commit.
- Do not add broad formatting-only changes across slice boundaries.
- Do not introduce dependencies unless they are recorded in `pyproject.toml` and justified in the relevant slice docs.
- If a change touches more than two slices, create an integration branch instead of stacking unrelated edits in one slice branch.

## Worktree Commands

Create worktrees from a clean `main`:

```powershell
git worktree add ..\mcp-bridge feature/mcp-bridge
git worktree add ..\mcp-registry feature/registry-policy
git worktree add ..\mcp-executor feature/executor-adapters
git worktree add ..\mcp-service feature/api-service
git worktree add ..\mcp-docs feature/install-docs
git worktree add ..\mcp-ci feature/ci-cd
```

Inspect worktrees:

```powershell
git worktree list
```

Remove a completed worktree after merge:

```powershell
git worktree remove ..\mcp-bridge
```

## Merge Gate

Before merging a slice branch:

- `git status --short` shows only intentional changes.
- Local CI check passes.
- GitHub Actions passes.
- Changed files stay inside the slice's owned paths, unless coordinated.
- Remaining risk is documented in the PR or commit message.

