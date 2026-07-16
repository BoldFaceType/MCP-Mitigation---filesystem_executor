# homecmd

`homecmd` is a local-first, policy-gated command gateway. Humans use the CLI
directly. Agent clients use the ACP service. MCP clients reach that ACP service
through the archived `acp-mcp==0.4.2` compatibility adapter with its compatible
`acp-sdk==0.8.4` dependency pinned explicitly.

## Architecture

```text
Human CLI  -> homecmd core
ACP client -> GET /agents, POST /runs -> homecmd core
MCP client -> pinned acp-mcp (stdio) -> ACP server -> homecmd core
```

The core runs only registered command cards. It does not provide a raw shell,
arbitrary code execution, filesystem API, MQTT command plane, or native MCP
worker endpoint.

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

Version 0.4.0 is a feature-branch preview, not a parity release. The direct
CLI, registry, policy, executor, audit, and ACP unit/integration paths pass.
The live pinned MCP adapter initializes and exposes `run_agent`, but its
`tools/call` currently receives `400 Invalid ACP run request` from the ACP
server. Previous LM Studio `call_worker`, filesystem, and MQTT use cases have
not yet been restored as bounded command cards.

See [the 2026-07-16 verification report](docs/verification/2026-07-16-v0.4.0-status.md)
for the exact checked and blocked boundaries.

## Token Efficiency

The v0.3.0 progressive-disclosure decisions remain, expressed through ACP:

- MCP loads the adapter's three generic tools, not one schema per command.
- `search` returns at most 20 compact summaries.
- `card` reveals one selected command contract on demand.
- ACP `run` returns at most 4,000 combined stdout/stderr characters.
- `log` retrieves the card-bounded full audit output only when requested.

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

Non-loopback binds require `HOMECMD_TOKEN` and an explicit
`HOMECMD_TLS_TERMINATED=true` assertion. See [OPERATIONS.md](OPERATIONS.md)
for deployment and verification.

## MCP Compatibility

Run the pinned stdio adapter while `homecmd-agent` is listening locally:

```bash
uvx --with acp-sdk==0.8.4 acp-mcp==0.4.2 http://127.0.0.1:8000
```

The adapter discovers ACP agents and exposes a `run_agent` MCP tool. End-to-end
command execution is still blocked by the ACP request mismatch described
above. The adapter is not part of the `homecmd` package and is not a new native
MCP API. The upstream adapter container is intentionally not documented as a
supported path because its image is unversioned.

Client examples:

- [Codex TOML](configs/mcp-clients/codex.toml)
- [Claude Desktop JSON](configs/mcp-clients/claude-desktop.json)
- [Activation and discovery](MCP_ACTIVATION_DISCOVERY.md)

## Development

```bash
python -m pytest
python scripts/ci_check.py
```
