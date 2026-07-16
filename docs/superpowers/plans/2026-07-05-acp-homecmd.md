# ACP-First Homecmd Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build an installable, policy-gated `homecmd` command service whose primary network interface is Agent Communication Protocol and whose MCP compatibility path is the existing `acp-mcp` adapter.

**Architecture:** A protocol-neutral application service owns registry lookup, policy decisions, execution, and audit records. The direct CLI and ACP agent both call that service. MCP clients run the external `acp-mcp` stdio adapter against the ACP server URL; they never access the executor directly.

**Tech Stack:** Python 3.11+, Pydantic 2, FastAPI/Uvicorn, synchronous inline text/JSON ACP compatibility subset, `acp-mcp==0.4.2`, `acp-sdk==0.8.4`, pytest, TOML command cards.

---

### Task 1: Package and Command Registry

**Files:**
- Create: `pyproject.toml`
- Create: `src/homecmd/__init__.py`
- Create: `src/homecmd/models.py`
- Create: `src/homecmd/registry.py`
- Create: `commands/core.toml`
- Test: `tests/test_registry.py`

- [x] Write tests proving compact search, exact card lookup, argument schema loading, and duplicate-ID rejection.
- [x] Run `python -m pytest tests/test_registry.py -q` and confirm imports or behavior fail because the package is missing.
- [x] Implement immutable command-card models and a TOML registry loader.
- [x] Run the registry tests and confirm they pass.

### Task 2: Policy, Safe Executor, and Audit Log

**Files:**
- Create: `src/homecmd/policy.py`
- Create: `src/homecmd/executor.py`
- Create: `src/homecmd/audit.py`
- Create: `configs/policy.local.toml`
- Create: `configs/policy.lan.toml`
- Test: `tests/test_policy_executor.py`

- [x] Write tests proving unknown commands and arguments fail closed, shell metacharacters remain inert argument data, writes require confirmation, destructive/network risks are denied by default, timeouts are enforced, and secret arguments are redacted in JSONL.
- [x] Run the focused tests and confirm expected failures.
- [x] Implement argument validation, policy decisions, `shell=False` execution, output limits, and audit persistence.
- [x] Run focused tests and the existing repository check.

### Task 3: Application Service and Direct CLI

**Files:**
- Create: `src/homecmd/app.py`
- Create: `src/homecmd/cli.py`
- Test: `tests/test_cli.py`

- [x] Write tests for `homecmd search`, `homecmd card`, `homecmd run`, and `homecmd log` using an isolated registry and audit path.
- [x] Verify the tests fail before implementation.
- [x] Implement an argparse CLI and shared application service.
- [x] Verify all CLI tests pass and help text lists exactly the four required commands plus `serve` for operations.

### Task 4: ACP Server

**Files:**
- Create: `src/homecmd/acp.py`
- Create: `src/homecmd/server.py`
- Test: `tests/test_acp.py`

- [x] Write tests for agent discovery and synchronous run requests using ACP message parts.
- [x] Verify the tests fail before implementation.
- [x] Implement one `homecmd-agent` whose JSON input selects `search`, `card`, `run`, or `log` and delegates to the shared service.
- [x] Enforce loopback default and require a token before non-loopback startup.
- [x] Verify ACP tests pass.

### Task 5: ACP-MCP Adapter and Operations

**Files:**
- Create: `configs/mcp-clients/codex.toml.example`
- Create: `configs/mcp-clients/claude-desktop.json.example`
- Modify: `README.md`
- Modify: `OPERATIONS.md`
- Modify: `MCP_ACTIVATION_DISCOVERY.md`
- Modify: `Dockerfile`

- [x] Document the double-pinned `uvx` adapter command; omit the unversioned adapter container image.
- [x] Document that ACP Communication Protocol is archived/merged into A2A and the dependency is isolated for replacement.
- [x] Replace raw `/execute` deployment guidance with registry command flows.
- [x] Add install, local serve, LAN auth, and adapter smoke commands.

### Task 6: CI and Completion Verification

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `scripts/ci_check.py`
- Modify: `CHANGELOG.md`
- Modify: `manifest_slices.md`
- Append: `AGENT_BOARD.jsonl`

- [x] Add pytest and package syntax/import checks to CI.
- [x] Run `python -m pytest` and confirm all tests pass.
- [x] Run `python scripts\ci_check.py` and confirm repository checks pass.
- [x] Run CLI search/card/run/log smoke tests.
- [x] Run ACP discovery/run smoke tests.
- [x] Append handoff and release board events with verification evidence.

Publication note (2026-07-16): local gates pass, but the external adapter
`tools/call` fails with `400 Invalid ACP run request`. The feature branch is a
WIP architecture preview until that compatibility gate passes.
