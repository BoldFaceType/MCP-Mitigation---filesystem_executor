# homecmd Operations

## Deployment Model

The shipping topology is ACP-first:

```text
Human CLI  -> homecmd core
ACP client -> homecmd-agent (/agents and /runs) -> homecmd core
MCP client -> pinned acp-mcp + acp-sdk -> homecmd-agent -> homecmd core
Worker MCP -> homecmd-agent (/mcp) -> call_worker only -> local LM Studio
```

There is no shipping deployment path for `/execute`, unrestricted filesystem
or MQTT routes, arbitrary shell input, or caller-selected worker backends.

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
| `HOMECMD_VAULT_ROOT` | unset | Required root for filesystem cards |
| `HOMECMD_POLICY` | read-only default | Optional policy TOML path |
| `LMSTUDIO_BASE_URL` | `http://127.0.0.1:1234/v1` | Fixed worker backend |
| `LMSTUDIO_MODEL` | first chat model | Optional fixed model ID |
| `WORKER_MAX_INPUT_CHARS` | `24000` | Worker task plus context cap |
| `WORKER_MAX_OUTPUT_CHARS` | `6000` | Worker response cap |
| `WORKER_TIMEOUT_SECONDS` | `120` | Worker timeout ceiling |

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

## Vault Cards

Configure one absolute operator-owned root:

```powershell
$env:HOMECMD_VAULT_ROOT = "C:\Dev\Obsidian-PKB-Active"
homecmd run filesystem.read path=03-Wiki/example.md
homecmd run filesystem.list path=03-Wiki
```

The default policy denies `filesystem.write`. Enable only the bounded write
risk when needed:

```powershell
$env:HOMECMD_POLICY = "configs\policy.vault-write.toml"
homecmd run filesystem.write path=03-Wiki/example.md 'content=# Updated'
```

The helper rejects absolute paths, traversal, and resolved symlink targets
outside the configured root. Writes are atomic. Vault content, filenames, and
write content are redacted from persistent audit records.

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

This smoke is a release gate. It must complete an actual MCP `tools/call`, not
only adapter initialization or discovery.

## Bounded Worker MCP

The same process exposes `POST /mcp` as a separate trust boundary. Its
`tools/list` response contains only `call_worker`. That tool sends bounded text
to the fixed local LM Studio base URL; it has no registry, command, filesystem,
Git, Docker, credential, or caller-selected network access.

```bash
python scripts/worker_smoke.py
```

The smoke starts the shipping server, performs a real MCP `tools/call`, and
requires nonempty LM Studio output. Worker audit events store the selected
model and character counts, never task, context, or response text.

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
- `POST /mcp` lists only `call_worker`.
- Non-loopback startup without `HOMECMD_TOKEN` fails.
- MCP clients start only the pinned `acp-mcp==0.4.2` plus `acp-sdk==0.8.4` stack.
- `python scripts/adapter_smoke.py` exits successfully before an MCP release.
- `python scripts/worker_smoke.py` completes a live LM Studio call.
- `python scripts/vault_smoke.py` completes a vault write/read/list round trip.
- No client or deployment path accepts arbitrary shell or code.
