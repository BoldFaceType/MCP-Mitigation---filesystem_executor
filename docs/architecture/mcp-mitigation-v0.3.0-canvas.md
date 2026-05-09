# MCP Mitigation v0.3.0 RepoReady Canvas

Date: 2026-05-09
Status: Architecture Ready / Implementation Ready

## Re-read, Rephrase, Respond

Re-read: reconcile the local FastAPI executor, the Drive/GitHub filesystem-executor plans, and the note that MCP is the tool protocol while CLI is the execution substrate.

Rephrase: build a token-efficient, secure, easy-to-install MCP client/server architecture where MCP is the compact protocol edge and a CLI/API command gateway owns discovery, policy, execution, and audit.

Respond: the product is `mcp-mitigation`, with `homecmd` as the human and agent-facing command gateway.

## Core Decision

Do not expose every local capability as a first-class MCP tool.

Expose a tiny MCP bridge:

- `cmd_search`
- `cmd_card`
- `cmd_run`
- `cmd_log`
- `cmd_cancel`

Put all real capabilities behind a registry-backed CLI/API gateway. This preserves MCP compatibility without loading large tool catalogs into the model context.

## Architecture

```text
MCP Client / AI App / Human
        |
        v
Thin MCP Bridge
  cmd_search
  cmd_card
  cmd_run
  cmd_log
  cmd_cancel
        |
        v
homecmd CLI/API Gateway
        |
        v
Command Registry + Policy Engine
        |
        v
Adapters: shell, python, docker, git, ollama, mqtt, home-assistant, filesystem
```

## How This Differs From Vanilla MCP

Vanilla MCP exposes structured tools directly through `tools/list` and `tools/call`. That is clear and portable, but large tool inventories create context overhead.

This architecture uses MCP as the protocol boundary and progressive disclosure layer:

- Always-loaded MCP surface: 5 compact gateway tools.
- On-demand discovery: concise command cards.
- Execution substrate: CLI/API gateway with validated arguments.
- Outputs: compact structured summaries with optional log/resource links.

## MCP Features Used

Use the current MCP specification primitives narrowly:

- Tools: compact gateway verbs only.
- Resources: command cards, logs, manifests, capability index.
- Roots: filesystem boundaries supplied by the client.
- Logging: redacted server audit events.
- Progress/tasks: long-running command status and cancellation.
- Authorization: required for Streamable HTTP or LAN deployments.
- Elicitation: optional future path for secure user-supplied secrets or approvals.
- Sampling: disabled by default; enable only for explicit higher-level workflows.

## Token Efficiency Pattern

Always loaded:

```text
cmd_search(goal)
cmd_card(command_id)
cmd_run(command_id, args, mode)
cmd_log(run_id)
cmd_cancel(run_id)
```

Discovered only when needed:

```yaml
id: docker.ps
summary: List Docker containers on approved host
risk: read
args:
  host: enum[p520, ser5, alienware]
example: homecmd run docker.ps host=p520
```

The model sees only the selected card, not the full registry.

## Security Model

Client-side security:

- Keep the MCP tool surface small.
- Do not expose raw shell execution to the model.
- Respect MCP roots for filesystem boundaries.
- Require explicit approval for write and destructive actions where the client supports it.
- Avoid server-initiated sampling unless explicitly enabled.
- Do not inject full registry contents into model context.

Server-side security:

- Default bind address is `127.0.0.1`.
- LAN binding requires bearer auth.
- Commands must be registered and allowlisted.
- Arguments must be Pydantic-validated.
- Risk classes: `read`, `write`, `destructive`, `secret`, `network`.
- `destructive` and `secret` commands are blocked by default.
- Every run gets timeout, output cap, redaction, and audit logging.
- Write commands should define dry-run and precheck behavior.

## Command Card Contract

```yaml
id: string
summary: string
risk: read|write|destructive|secret|network
adapter: shell|python|docker|git|ollama|mqtt|home_assistant|filesystem
args: object
requires_confirm: boolean
timeout_seconds: integer
max_output_chars: integer
example: string
precheck: string|null
dry_run: string|null
```

## VSA Repo Layout

```text
mcp-mitigation/
  pyproject.toml
  README.md
  CHANGELOG.md
  .env.example
  configs/
    homecmd.yaml
    policy.local.yaml
    policy.lan.yaml
  src/mcp_mitigation/
    bridge_mcp/
    homecmd/
    registry/
    policy/
    executor/
    adapters/
    audit/
    service/
  commands/
    core.yaml
    docker.yaml
    git.yaml
    ollama.yaml
    mqtt.yaml
  tests/
  docs/
```

## VSA Slices

Slice 1: MCP Bridge

- Owns `src/mcp_mitigation/bridge_mcp`.
- Exposes only `cmd_search`, `cmd_card`, `cmd_run`, `cmd_log`, and `cmd_cancel`.
- Tests verify MCP tool schemas remain compact.

Slice 2: Command Registry

- Owns `src/mcp_mitigation/registry` and `commands`.
- Loads YAML command cards.
- Supports keyword search and exact card reads.

Slice 3: Policy Engine

- Owns `src/mcp_mitigation/policy` and `configs/policy.*.yaml`.
- Enforces risk, confirmation, path, network, timeout, and output policies.

Slice 4: Execution Substrate

- Owns `src/mcp_mitigation/executor`.
- Runs approved commands non-interactively.
- Handles timeout, cancellation, stdout/stderr capture, and structured result creation.

Slice 5: Adapters

- Owns `src/mcp_mitigation/adapters`.
- Provides bounded integrations for shell, docker, git, ollama, mqtt, Home Assistant, and filesystem.

Slice 6: API Service

- Owns `src/mcp_mitigation/service`.
- Provides `GET /search`, `GET /card/{id}`, `POST /run/{id}`, `GET /log/{run_id}`, and `POST /cancel/{run_id}`.

Slice 7: Audit and Redaction

- Owns `src/mcp_mitigation/audit`.
- Writes `audit.jsonl`.
- Redacts secrets, tokens, private keys, and high-risk environment output.

Slice 8: Install and Ops

- Owns README, docs, service templates, examples, and troubleshooting.
- Keeps install path simple for non-developer users.

## Parallel Worktrees

```powershell
git worktree add ../mcp-bridge feature/mcp-bridge
git worktree add ../mcp-registry feature/registry-policy
git worktree add ../mcp-executor feature/executor-adapters
git worktree add ../mcp-service feature/api-service
git worktree add ../mcp-docs feature/install-docs
```

## Install Flow

Preferred user flow:

```powershell
pipx install mcp-mitigation
homecmd init
homecmd doctor
homecmd serve --profile local
```

Local MCP client config:

```json
{
  "mcpServers": {
    "mcp-mitigation": {
      "command": "mcp-mitigation-mcp",
      "args": ["--config", "C:/Users/jerem/.mcp-mitigation/config.yaml"]
    }
  }
}
```

LAN profile:

```yaml
server:
  host: 0.0.0.0
  port: 8000
auth:
  required: true
policy: policy.lan.yaml
```

## MVP Scope

Ship only:

- `homecmd search`
- `homecmd card`
- `homecmd run`
- `homecmd log`
- `homecmd cancel`
- `mcp-mitigation-mcp`
- `commands/core.yaml`
- `audit.jsonl`

Initial commands:

- `git.status`
- `git.diff`
- `docker.ps`
- `docker.logs`
- `docker.restart`
- `ollama.list`
- `mqtt.publish`
- `mqtt.read`
- `filesystem.read`
- `system.gpu`

## CI Gates

Required before merge:

- `python -m compileall src`
- unit tests
- command-card schema validation
- policy validation
- redaction tests
- MCP bridge schema size check
- smoke test for `homecmd search/card/run`

## Trade-offs

This architecture gives up rich per-tool MCP schemas at the protocol edge. In return, it keeps context small, makes commands debuggable by humans, and centralizes security in one policy layer.

The main risk is accidentally creating an unsafe shell proxy. The mitigation is strict registry allowlisting, typed arguments, risk policy, audit logging, and no arbitrary shell passthrough.

## Implementation Order

1. Define models: `CommandCard`, `RunRequest`, `RunResult`, `PolicyDecision`.
2. Build registry load/search/card.
3. Build policy validation and audit.
4. Build non-interactive executor.
5. Build CLI commands.
6. Add FastAPI service.
7. Add MCP bridge.
8. Add docs, install scripts, and CI.

## Source Context

- Local FastAPI prototype: `C:/Dev/projects/mcp-mitigation`
- GitHub repo: `BoldFaceType/MCP-Mitigation---filesystem_executor`
- Drive docs: MCP Bootstrap Layer, MCP-Mitigation Filesystem Executor, MCP Code Execution Reference
- Attached note: `MCP - tool protocol_CLI - execution substrate.md`
- MCP spec checked via Context7: `modelcontextprotocol.io` 2025-11-25 specification
