# MCP Activation and Discovery

Date: 2026-07-16

## Decision

`homecmd` is ACP-first for command execution and ships a second, bounded MCP
worker endpoint for local-model delegation.

```text
MCP client -> pinned acp-mcp + acp-sdk over stdio -> ACP server -> homecmd core
External/bounded MCP client -> POST /mcp -> call_worker only -> local LM Studio
```

Human users call the `homecmd` CLI directly. ACP clients discover agents with
`GET /agents` and create synchronous runs with `POST /runs`. Trusted MCP
command clients start the archived adapter as a local stdio child process.
Clients that need only model delegation use the separately bounded `/mcp`
endpoint and discover exactly `call_worker`.

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

## Bounded Worker Discovery

The native worker plane is available at:

```text
http://127.0.0.1:8000/mcp
```

Its JSON-RPC discovery result is exactly one tool:

```text
tools/list -> call_worker
```

The endpoint does not expose command cards, shell, filesystem, Git, Docker,
MQTT, credentials, or caller-selected URLs. For LAN or external use, publish
only this path through an authenticated TLS gateway. Do not publish `/runs` or
the ACP adapter to untrusted model clients.

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

Command-plane MCP discovery exposes the adapter's translation of ACP agents.
The homecmd ACP agent accepts only `search`, `card`, `run`, and `log` payloads,
and a `run` request must name a registered command card. Worker-plane MCP
discovery exposes only `call_worker` and cannot reach the command core.

The following are not shipping discovery or deployment surfaces:

- `/execute`
- raw or unrestricted filesystem tools
- MQTT command tools
- arbitrary shell or caller-controlled interpreter source
- Docker integration or unrestricted Git execution

## Token Boundary

The adapter's generic MCP tools replace the former five-tool custom bridge.
`run_agent` carries compact `search`, `card`, `run`, and `log` operations.
Search returns at most 20 summaries, and ACP run output is a 4,000-character
preview with full card-bounded output available through an explicit log call.
Synchronous execution makes `cancel` inapplicable in v0.4.0.

The worker plane adds one always-loaded schema rather than exposing local-model
management operations. Task/context input is capped at 24,000 characters and
output at 6,000 characters by default.

Adding a new command requires a reviewed registry card and policy coverage; it
must not be introduced by broadening the protocol adapter.
