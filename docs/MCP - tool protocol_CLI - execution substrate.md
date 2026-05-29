# MCP is the tool protocol. CLI/API is the execution substrate.

The problem is not "how do I expose every local capability as an MCP tool?"

The problem is compact capability discovery plus safe command routing.

Do not expose 80 MCP tools if 5 compact CLI verbs can discover and invoke the same approved capability surface. The local system should stay debuggable from a terminal, callable from local agents, and bridgeable to MCP without loading the entire home-lab schema into every model context.

## Architecture

```text
AI / Agent / Human CLI
        |
        v
homecmd
one tiny CLI/API gateway
        |
        |-- search
        |-- card
        |-- help
        |-- run
        |-- log
        v
Command Registry
commands.yaml / SQLite
id, tags, args, risk, host, adapter
        |
        v
Adapters
docker | ha | frigate | git | ollama | lmstudio | task | just | ssh | rsync | nvidia
```

Recommended name: `homecmd`.

Avoid a clever name. The system should describe what it does.

## Core idea

The always-loaded model contract is small:

```text
homecmd search "<goal>"
homecmd card <command_id>
homecmd help <command_id>
homecmd run <command_id> key=value ...
homecmd log <run_id>
```

Everything else is discovered on demand.

This keeps the token efficiency of CLI workflows while preserving MCP-like discoverability.

## Two access planes

This design has two separate planes. They must not collapse into one surface.

| Plane | Caller | Interface | Capability |
| --- | --- | --- | --- |
| Local control plane | Local human, local agent, local MCP client | `homecmd` CLI/API and thin MCP bridge | Discover and run approved local commands |
| Bounded worker plane | Non-local foundation model | One MCP tool: `call_worker` | Delegate busy work to a local LM Studio worker |

The local control plane is for trusted local operation.

The bounded worker plane is for external foundation models such as Gemini, Claude, ChatGPT, and DeepSeek. It exists only so those models can orchestrate local inference and save paid tokens. It must not expose the local command registry.

## Local control plane

Expose `homecmd` three ways:

1. CLI
2. Local HTTP API
3. Thin local MCP bridge

### CLI

```text
homecmd search "restart frigate"
homecmd card frigate.restart
homecmd help frigate.restart
homecmd run frigate.restart host=p520
homecmd log 2026-05-08T22:31:02Z-frigate-restart
```

### Local HTTP API

```text
GET  /search?q=frigate
GET  /card/frigate.restart
GET  /help/frigate.restart
POST /run/frigate.restart
GET  /log/{run_id}
```

### Local MCP bridge

The local MCP bridge should expose only the compact command verbs:

```text
cmd_search
cmd_card
cmd_help
cmd_run
cmd_log
cmd_explain_error
```

It is a compatibility layer, not the main registry.

```text
Local MCP client
        |
        v
tiny MCP bridge
        |
        v
homecmd API
        |
        v
CLI registry/adapters
```

## Bounded worker plane for foundation models

Foundation models must not receive direct access to `cmd_run`, shell, Docker, filesystem, Git, Home Assistant, Frigate, credentials, or the full command registry.

They get one tool only:

```text
call_worker
```

The foundation model remains the orchestrator. The local model does delegated busy work.

```text
Gemini / Claude / ChatGPT / DeepSeek
        |
        v
bounded MCP endpoint
tool: call_worker
        |
        v
worker broker
        |
        v
LM Studio local model
        |
        v
bounded result back to foundation model
```

Ollama can be added later behind the same broker. The external MCP contract should not change when Ollama support is added.

### `call_worker` contract

`call_worker` accepts one bounded task request and returns one bounded worker result.

Input:

```json
{
  "task": "Summarize this diff and identify likely test impact.",
  "context": "Small bounded context supplied by the foundation model.",
  "worker_profile": "default",
  "max_output_chars": 6000,
  "timeout_seconds": 120
}
```

Output:

```json
{
  "ok": true,
  "worker_id": "lmstudio.default",
  "run_id": "2026-05-28T21-44-12Z-worker",
  "summary": "Short answer from the local worker.",
  "result": "Bounded worker output.",
  "truncated": false
}
```

Failure:

```json
{
  "ok": false,
  "worker_id": "lmstudio.default",
  "run_id": "2026-05-28T21-44-12Z-worker",
  "error": "timeout",
  "message": "Worker exceeded timeout_seconds.",
  "truncated": false
}
```

### Required worker-plane restrictions

`call_worker` must be intentionally weaker than the local command plane.

Required restrictions:

- Exactly one exposed MCP tool: `call_worker`.
- No command discovery.
- No command execution.
- No arbitrary URL fetch.
- No filesystem access unless a future local policy explicitly injects selected content.
- No shell access.
- No credential, environment, SSH, Docker socket, or Git remote access.
- Bounded input size.
- Bounded output size.
- Timeout per call.
- Audit log per call.
- Local allowlist for worker backend: initially LM Studio only.
- Ollama support is a later backend option, not a new external tool.

The worker may reason, summarize, draft, classify, transform, or decompose tasks using only the context provided to it. It may not independently operate the local machine.

### Worker broker

The broker is the internal adapter that turns `call_worker` into a local inference request.

Initial backend:

```text
LM Studio OpenAI-compatible local API
```

Later backend:

```text
Ollama local API
```

The broker owns:

- Backend selection.
- Prompt wrapping.
- Timeout.
- Output truncation.
- Audit logging.
- Error normalization.
- Worker profile mapping.

Example worker profiles:

```yaml
worker_profiles:
  default:
    backend: lmstudio
    model: local-default
    temperature: 0.2
    max_tokens: 2048
  code_review:
    backend: lmstudio
    model: local-coder
    temperature: 0.1
    max_tokens: 4096
```

The foundation model may request a profile by name. It may not choose raw backend URLs, arbitrary models, or local file paths.

## Command object

Each local command in the registry should be small.

```json
{
  "id": "frigate.camera.snapshot",
  "summary": "Capture latest Frigate snapshot for a camera",
  "tags": ["frigate", "camera", "snapshot", "image"],
  "risk": "read",
  "host": "p520",
  "adapter": "frigate",
  "args": {
    "camera": "string"
  },
  "example": "homecmd run frigate.camera.snapshot camera=front_door"
}
```

The model needs:

```text
id + purpose + args + risk + example
```

It does not need long prose for every capability.

## Discovery flow

### Step 1: search

```text
homecmd search "restart frigate"
```

Returns compact JSON:

```json
[
  {
    "id": "frigate.service.restart",
    "summary": "Restart Frigate container",
    "risk": "write",
    "args": ["host"]
  },
  {
    "id": "frigate.service.status",
    "summary": "Show Frigate container status",
    "risk": "read",
    "args": ["host"]
  }
]
```

### Step 2: inspect only the selected command

```text
homecmd card frigate.service.restart
```

Returns:

```json
{
  "id": "frigate.service.restart",
  "risk": "write",
  "requires_confirm": true,
  "args": {
    "host": {
      "enum": ["p520", "ser5", "alienware"]
    }
  },
  "dry_run": "docker --context p520 restart frigate",
  "example": "homecmd run frigate.service.restart host=p520"
}
```

### Step 3: run

```text
homecmd run frigate.service.restart host=p520
```

Returns:

```json
{
  "ok": true,
  "run_id": "2026-05-08T22:31:02Z-frigate-restart",
  "stdout": "frigate",
  "exit_code": 0
}
```

## Best substrate: Taskfile plus thin registry

Use Taskfile as the first implementation substrate, not pure Python from scratch.

| Option | Verdict |
| --- | --- |
| Raw Bash scripts | Simple but messy discovery |
| `just` | Excellent local command runner |
| Taskfile | Better for machine-readable discovery |
| Full MCP | Too much overhead for the core local problem |
| Custom orchestration framework | Scope creep unless Taskfile fails |

Recommended split:

| Layer | Tool |
| --- | --- |
| Home/server automation | Taskfile |
| Repo-local developer commands | justfile |
| Unified discovery and policy wrapper | `homecmd` |
| Local model delegation | `call_worker` broker |

## Minimal file layout

KISS version:

```text
homecmd/
  commands.yaml
  policy.yaml
  worker_profiles.yaml
  homecmd.py
  worker_broker.py
  audit.jsonl
```

Expanded version:

```text
homecmd/
  commands/
    home.yaml
    docker.yaml
    frigate.yaml
    home_assistant.yaml
    models.yaml
    git.yaml
  adapters/
    docker.py
    ha.py
    frigate.py
    ollama.py
    lmstudio.py
    task.py
    just.py
  registry.sqlite
  policy.yaml
  worker_profiles.yaml
  homecmd.py
  worker_broker.py
  audit.jsonl
```

Start with the KISS version.

## Example `commands.yaml`

```yaml
commands:
  docker.ps:
    summary: List Docker containers on a host
    risk: read
    adapter: shell
    host_arg: host
    args:
      host:
        enum: [p520, ser5, alienware]
    cmd: "docker --context {host} ps --format json"

  frigate.restart:
    summary: Restart Frigate container
    risk: write
    requires_confirm: true
    adapter: shell
    args:
      host:
        enum: [p520, ser5]
    cmd: "docker --context {host} restart frigate"

  ollama.list_models:
    summary: List local Ollama models
    risk: read
    adapter: shell
    args:
      host:
        enum: [alienware, p520]
    cmd: "ssh {host} 'ollama list'"

  ha.call_service:
    summary: Call approved Home Assistant service
    risk: write
    requires_confirm: true
    adapter: home_assistant
    args:
      service:
        enum:
          - light.turn_on
          - light.turn_off
          - media_player.turn_off
      entity_id:
        type: string
```

The registry is the tool schema, but models only see slices of it.

## Output policy

Command output must be token-efficient.

Bad:

```text
docker ps
```

Better:

```text
docker ps --format json
```

Best:

```text
homecmd run docker.ps host=p520 --compact
```

Returns:

```json
[
  {"name": "frigate", "state": "running", "status": "healthy"},
  {"name": "open-webui", "state": "running", "status": "running"}
]
```

Principle:

```text
CLI in. Structured JSON out. Summarized before reaching the model.
```

Do not make the model parse noisy terminal output unless necessary.

## Risk policy

For local network tasks, classify commands:

| Risk | Examples | Confirmation |
| --- | --- | --- |
| `read` | status, list, logs, GPU info | No |
| `write` | restart container, toggle light | Yes for first version |
| `destructive` | delete, prune, format, remove volume | Block initially |
| `secret` | tokens, credentials, env dumps | Block |
| `network` | download, curl external, package install | Block or explicit allow |

Policy file:

```yaml
defaults:
  max_output_chars: 12000
  timeout_seconds: 30
  require_json_output: false
  log_all_runs: true

bounded_worker:
  enabled: true
  exposed_tools: [call_worker]
  allowed_backends: [lmstudio]
  future_backends: [ollama]
  max_input_chars: 24000
  max_output_chars: 6000
  timeout_seconds: 120
  log_all_runs: true
  allow_filesystem: false
  allow_shell: false
  allow_command_registry: false
  allow_network_fetch: false

blocked_patterns:
  - "rm -rf"
  - "sudo"
  - "curl | sh"
  - "wget | sh"
  - "docker system prune"
  - "cat ~/.ssh"
  - "printenv"
  - "env"

risk_rules:
  destructive:
    allowed: false
  write:
    require_confirm: true
  read:
    require_confirm: false
```

## Highest-VCR MVP

Build only this for the local control plane:

```text
homecmd search
homecmd card
homecmd run
homecmd log
```

Back it with:

```text
commands.yaml
policy.yaml
audit.jsonl
subprocess runner
timeout
allowlist
max output limit
```

Initial command namespaces:

```text
git.*
docker.*
frigate.*
ha.*
ollama.*
lmstudio.*
system.*
```

First local commands:

```text
git.status
git.diff
docker.ps
docker.logs
docker.restart
frigate.status
frigate.restart
ha.state
ollama.list
lmstudio.models
nvidia.smi
```

Build only this for the bounded worker plane:

```text
call_worker
```

Back it with:

```text
worker_profiles.yaml
worker_broker.py
LM Studio OpenAI-compatible endpoint
timeout
input/output limits
audit log
```

## Non-goals

Do not build these in the first version:

- A general remote command execution endpoint.
- A public API for the command registry.
- Direct foundation-model access to `homecmd run`.
- Full multi-worker scheduling.
- Arbitrary file upload or filesystem browse.
- Long-running autonomous local agents.
- Ollama backend unless LM Studio delegation is already working.

## Final verdict

The core local system is:

```text
homecmd = internal command server
      + compact discovery
      + CLI-native execution
      + JSON output
      + policy guardrails
      + audit logs
      + optional local MCP bridge
```

The bounded external model system is:

```text
call_worker = one-tool MCP endpoint
           + LM Studio worker delegation
           + strict input/output bounds
           + no command registry access
           + no shell/filesystem/network fetch
           + audit logs
           + future Ollama backend behind the same contract
```

That gives local agents a usable command substrate and gives non-local foundation models a safe way to delegate busy work to local inference without exposing the machine.
