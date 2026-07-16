# MCP Activation and Discovery

Date: 2026-07-05

## Decision

`homecmd` is ACP-first. It does not ship a native MCP endpoint.

```text
MCP client -> pinned acp-mcp + acp-sdk over stdio -> ACP server -> homecmd core
```

Human users call the `homecmd` CLI directly. ACP clients discover agents with
`GET /agents` and create synchronous runs with `POST /runs`. MCP clients start
the official archived adapter as a local stdio child process.

## Compatibility Status

IBM/BeeAI ACP and the official `i-am-bee/acp-mcp` adapter were archived when
ACP merged into Agent2Agent (A2A) under the Linux Foundation. Versions
`acp-mcp==0.4.2` and `acp-sdk==0.8.4` form the pinned compatibility boundary
for this repository. The adapter's declared SDK lower bound is insufficient;
`acp-sdk==1.0.3` breaks its `run_agent` session call. A2A is the future target.

Do not use an unpinned Python adapter version. Do not interpret the adapter as
an actively maintained protocol layer.

## Start the ACP Server

```bash
homecmd-agent
```

Verify discovery:

```bash
curl http://127.0.0.1:8000/agents
```

The response must include `homecmd-agent`. The service default is loopback-only.

## Start the MCP Adapter

Preferred pinned command:

```bash
uvx --with acp-sdk==0.8.4 acp-mcp==0.4.2 http://127.0.0.1:8000
```

The adapter communicates with the MCP client over stdio, discovers ACP agent
resources, and exposes `run_agent` for invocation. The upstream unversioned
container image is not part of this repository's supported deployment path.

## Codex

Merge [configs/mcp-clients/codex.toml](configs/mcp-clients/codex.toml) into
`~/.codex/config.toml`, or use it as project configuration at
`.codex/config.toml` in a trusted repository. Restart Codex, then inspect the
active server with `/mcp`.

The example allows only `run_agent` and leaves tool approval in prompt mode.

## Claude Desktop

Merge [configs/mcp-clients/claude-desktop.json](configs/mcp-clients/claude-desktop.json)
into `%APPDATA%\Claude\claude_desktop_config.json`, then restart Claude
Desktop. The adapter registers the ACP agent as a resource and exposes its
`run_agent` tool.

## Discovery Boundary

MCP discovery exposes the adapter's translation of ACP agents. The homecmd ACP
agent still accepts only `search`, `card`, `run`, and `log` payloads. A `run`
request must name a registered command card.

The following are not shipping discovery or deployment surfaces:

- `/execute`
- raw filesystem tools
- MQTT command tools
- a native `/mcp` or `call_worker` endpoint
- arbitrary shell, Python source, Docker, or Git execution

## Token Boundary

The adapter's generic MCP tools replace the former five-tool custom bridge.
`run_agent` carries compact `search`, `card`, `run`, and `log` operations.
Search returns at most 20 summaries, and ACP run output is a 4,000-character
preview with full card-bounded output available through an explicit log call.
Synchronous execution makes `cancel` inapplicable in v0.4.0.

Adding a new command requires a reviewed registry card and policy coverage; it
must not be introduced by broadening the protocol adapter.
