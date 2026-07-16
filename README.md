# homecmd

`homecmd` is a local-first, policy-gated command gateway. Humans use the CLI,
agent clients use ACP, and MCP command clients use the pinned ACP adapter. A
separate native MCP worker endpoint exposes exactly one bounded LM Studio tool.

## Architecture

```text
Human CLI  -> homecmd core
ACP client -> GET /agents, POST /runs -> homecmd core
MCP client -> pinned acp-mcp (stdio) -> ACP server -> homecmd core
Worker MCP -> POST /mcp -> call_worker only -> local LM Studio
```

The command core runs only registered cards. Vault operations are fixed cards
scoped to `HOMECMD_VAULT_ROOT`; there is no raw filesystem API. The worker MCP
endpoint has no path to the registry, executor, shell, filesystem, Git, Docker,
credentials, or caller-selected network destinations.

The dated architecture baseline is the
[v0.4.0 RepoReady Canvas](docs/architecture/mcp-mitigation-v0.4.0-canvas.md).

## Compatibility Boundary

IBM/BeeAI's Agent Communication Protocol (ACP) and the official `acp-mcp`
adapter were archived after ACP merged into Agent2Agent (A2A) under the Linux
Foundation. This repository intentionally retains the ACP HTTP contract and
pins `acp-mcp==0.4.2` and `acp-sdk==0.8.4` as one compatibility boundary.
`acp-mcp` declares only a lower SDK bound, but its `run_agent` implementation
is incompatible with `acp-sdk==1.0.3`. Migration to A2A is the future protocol
target; do not silently upgrade either pin.

The server intentionally implements the synchronous inline text/JSON subset
used by the adapter, not every archived ACP feature.

## Current Status

Version 0.4.0 has verified parity for the approved local use cases: direct CLI,
ACP, MCP-to-ACP `tools/call`, bounded LM Studio `call_worker`, Obsidian vault
read/list/write, and fixed Git inspection cards. It intentionally does not
restore the previous raw execution, unrestricted filesystem, or MQTT routes.
Docker remains outside this deployment, and MQTT/Ollama cards are omitted
because their CLIs are not installed or required by the current use cases.

See [the 2026-07-16 verification report](docs/verification/2026-07-16-v0.4.0-status.md)
for exact commands and boundaries.

## Token Efficiency

The v0.3.0 progressive-disclosure decisions remain, expressed through ACP:

- MCP loads the adapter's three generic tools, not one schema per command.
- `search` returns at most 20 compact summaries.
- `card` reveals one selected command contract on demand.
- ACP `run` returns at most 4,000 combined stdout/stderr characters.
- `log` retrieves the card-bounded full audit output only when requested.
- The separate worker plane exposes one MCP schema: `call_worker`.

The former five custom MCP tools are not restored because `run_agent` carries
the four logical operations over the existing adapter. `cancel` is omitted
while runs are synchronous; command-card MCP resources would require a custom
adapter and duplicate the discovery path.

## Install

Python 3.11 or newer is required.

```bash
python -m pip install .
```

Only dependencies declared in `pyproject.toml` are installed.

## Human CLI

```bash
homecmd search version
homecmd card system.python_version
homecmd run system.python_version
homecmd log <run-id>
```

`homecmd run` accepts a registered command ID and validated `key=value`
arguments. It never accepts shell source or an arbitrary executable.

## Obsidian Vault

Set a single vault root. Reads and listings use the default read-only policy;
writes require the explicit vault-write policy.

```powershell
$env:HOMECMD_VAULT_ROOT = "C:\Dev\Obsidian-PKB-Active"
homecmd run filesystem.read path=03-Wiki/example.md
homecmd run filesystem.list path=03-Wiki
$env:HOMECMD_POLICY = "configs\policy.vault-write.toml"
homecmd run filesystem.write path=03-Wiki/example.md content="# Updated"
```

Absolute paths, traversal, and resolved paths outside the configured root are
rejected. Vault content and filenames are returned to the caller but redacted
from persistent audit output; write content is also redacted from arguments.

## ACP Server

Start the default loopback-only service:

```bash
homecmd-agent
```

The ACP surface is:

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/agents`
- `GET http://127.0.0.1:8000/agents/homecmd-agent`
- `POST http://127.0.0.1:8000/runs`
- `POST http://127.0.0.1:8000/mcp` (bounded worker plane only)

Non-loopback binds require `HOMECMD_TOKEN` and an explicit
`HOMECMD_TLS_TERMINATED=true` assertion. See [OPERATIONS.md](OPERATIONS.md)
for deployment and verification.

## MCP Compatibility

Run the pinned stdio adapter while `homecmd-agent` is listening locally:

```bash
uvx --with acp-sdk==0.8.4 acp-mcp==0.4.2 http://127.0.0.1:8000
```

The adapter discovers ACP agents and exposes `run_agent`; its live
`initialize -> tools/list -> tools/call` path is verified. It remains an
archived compatibility dependency, separate from the native one-tool worker
endpoint. The upstream adapter container is not supported because its image is
unversioned.

## Bounded Worker

`POST /mcp` exposes exactly `call_worker`. The task and optional context are
bounded, LM Studio is the only configured destination, output is capped, and
the audit stores sizes/model/status without prompt or response content.

Configuration defaults are shown in [.env.example](.env.example). Verify a
live local model with:

```bash
python scripts/worker_smoke.py
```

Client examples:

- [Codex TOML](configs/mcp-clients/codex.toml)
- [Claude Desktop JSON](configs/mcp-clients/claude-desktop.json)
- [Activation and discovery](MCP_ACTIVATION_DISCOVERY.md)

## Development

```bash
python -m pytest
python scripts/ci_check.py
python scripts/adapter_smoke.py
python scripts/worker_smoke.py
python scripts/vault_smoke.py
```
