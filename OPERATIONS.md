# homecmd Operations

## Deployment Model

The shipping topology is ACP-first:

```text
Human CLI  -> homecmd core
ACP client -> homecmd-agent (/agents and /runs) -> homecmd core
MCP client -> pinned acp-mcp + acp-sdk -> homecmd-agent -> homecmd core
```

There is no shipping deployment path for `/execute`, raw filesystem tools,
MQTT command tools, a native `/mcp` worker, or arbitrary shell input.

## Install and Start

```bash
python -m pip install .
homecmd-agent
```

Defaults:

| Setting | Default | Purpose |
|---|---|---|
| `HOMECMD_HOST` | `127.0.0.1` | Loopback-only bind |
| `HOMECMD_PORT` | `8000` | ACP HTTP port |
| `HOMECMD_COMMANDS` | packaged `core.toml` | Registered command catalog |
| `HOMECMD_AUDIT_LOG` | `~/.homecmd/audit.jsonl` | Redacted run audit log |
| `HOMECMD_TOKEN` | unset | Required for any non-loopback bind |
| `HOMECMD_TLS_TERMINATED` | unset | Must be true for a non-loopback bind after TLS termination |

`homecmd serve --host 127.0.0.1 --port 8000` is equivalent to the default
entry point. Development reload mode is intentionally not used.

## Service Checks

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/agents
```

Expected discovery includes one agent named `homecmd-agent`.

Run a registered operation through ACP:

```bash
curl -X POST http://127.0.0.1:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"homecmd-agent","mode":"sync","input":[{"role":"user","parts":[{"content_type":"application/json","content":"{\"operation\":\"run\",\"command_id\":\"system.python_version\",\"args\":{}}"}]}]}'
```

Supported operation payloads are `search`, `card`, `run`, and `log`. The `run`
operation accepts only registered command IDs and validated arguments.

## Authentication and Binding

Loopback is the default trust boundary. A non-loopback bind fails at startup
unless `HOMECMD_TOKEN` is set and `HOMECMD_TLS_TERMINATED=true`. The TLS
setting is an operator assertion: set it only when a trusted reverse proxy or
service mesh terminates TLS before traffic reaches `homecmd-agent`. ACP
requests then require:

```text
Authorization: Bearer <HOMECMD_TOKEN>
```

`/health` remains unauthenticated for local process supervision. Do not bind to
`0.0.0.0` without a token, and do not publish the service directly to an
untrusted network.

## Docker Image

Build the package image:

```bash
docker build -t homecmd-agent:0.4.0 .
```

The image installs this repository as a Python package and starts
`homecmd-agent` without `--reload`. Its default bind remains `127.0.0.1`.

The image runs as an unprivileged `homecmd` user. Its default loopback bind is
useful for in-container checks but is intentionally unreachable through a
published Docker port.

For a networked container, place it behind a TLS-terminating reverse proxy,
enable the internal non-loopback bind, and supply a token:

```bash
docker run --rm \
  -e HOMECMD_HOST=0.0.0.0 \
  -e HOMECMD_TOKEN=replace-with-a-secret \
  -e HOMECMD_TLS_TERMINATED=true \
  --network homecmd-private \
  homecmd-agent:0.4.0
```

Do not publish the application container directly. Publish the reverse
proxy's TLS port and keep `homecmd-private` isolated from untrusted workloads.

## MCP Adapter

For MCP clients, run the pinned archived adapter against a loopback
`homecmd-agent` process:

```bash
uvx --with acp-sdk==0.8.4 acp-mcp==0.4.2 http://127.0.0.1:8000
```

The adapter uses stdio for the MCP client connection; do not publish an adapter
port. Both pins are required. The adapter's open-ended `acp-sdk>=0.8.4`
dependency otherwise resolves `1.0.3`, whose client session API is incompatible
with `acp-mcp==0.4.2`. The upstream container image is unversioned and is not a
supported reproducible deployment path here.

After installing this package and `uv`, run the live compatibility smoke test:

```bash
python scripts/adapter_smoke.py
```

The script starts a temporary loopback ACP server, initializes the pinned
adapter over MCP stdio, requires `tools/list` to expose `run_agent`, and calls
that tool to execute `system.python_version` through ACP. It is kept out of
routine CI because it downloads and executes an archived external package.

Current release gate: discovery succeeds, but the live `tools/call` fails
because `homecmd-agent` returns `400 Invalid ACP run request`. Treat the MCP
adapter path as unavailable until this smoke command exits successfully. The
direct CLI and ACP tests do not substitute for this external compatibility
gate.

## Token-Efficient Use

For agent callers, use `search`, then one `card`, then `run`. Search is capped
at 20 summaries. ACP run responses include a maximum 4,000-character combined
stdout/stderr preview; use `log` only when the full card-bounded output is
actually needed. There is no `cancel` operation while execution is synchronous.

IBM/BeeAI ACP and `acp-mcp` were archived after ACP merged into A2A. Treat this
adapter as frozen compatibility code and track A2A as the migration target.

## Verification Checklist

- `homecmd search version` lists approved command cards.
- `GET /health` returns `{"status":"ok"}`.
- `GET /agents` lists `homecmd-agent`.
- `POST /runs` completes an approved operation.
- Non-loopback startup without `HOMECMD_TOKEN` fails.
- MCP clients start only the pinned `acp-mcp==0.4.2` plus `acp-sdk==0.8.4` stack.
- `python scripts/adapter_smoke.py` exits successfully before an MCP release.
- No client or deployment path accepts arbitrary shell or code.
