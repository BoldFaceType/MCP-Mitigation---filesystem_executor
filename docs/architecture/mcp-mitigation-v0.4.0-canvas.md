# MCP Mitigation v0.4.0 RepoReady Canvas

Date: 2026-07-16
Status: RepoReady / Approved Use-Case Parity Verified

## Rule Of One

`homecmd` solves one problem: execute operator-registered local commands through
one policy and audit boundary, regardless of whether the caller is a human,
an ACP client, or an MCP client.

## Decision

ACP is the primary network protocol. MCP compatibility is delegated to the
existing `acp-mcp==0.4.2` adapter with `acp-sdk==0.8.4`. Human operators retain
a direct CLI.

```text
Human CLI   -> homecmd CLI       -> registry -> policy -> executor -> audit
ACP client  -> homecmd-agent     -> registry -> policy -> executor -> audit
MCP client  -> acp-mcp adapter   -> homecmd-agent -> same core
Worker MCP  -> /mcp call_worker  -> bounded local LM Studio client
```

The adapter and ACP protocol are archived compatibility boundaries. A2A is the
future migration target; replacing ACP must not change the core service API.

## Value And Trade-Offs

Value:

- One command contract and one enforcement path.
- Compact discovery through `search` and `card` instead of a large tool list.
- No arbitrary shell, source-code, filesystem, MQTT, Docker, or Git passthrough.
- Vault cards resolve beneath one operator-configured root.
- The separate worker plane exposes one tool and cannot reach the command core.
- Direct CLI remains usable when no agent protocol is needed.
- Command-plane MCP clients reuse the existing adapter; the native worker route
  restores the previous one-tool external trust boundary.

Trade-offs:

- ACP and the adapter are archived and must remain pinned.
- MCP adds one local stdio process and one translation hop.
- Rich per-command MCP schemas are replaced by compact command-card discovery.
- A2A migration remains future work.

## Runtime Contract

Human CLI commands:

```text
homecmd search <terms>
homecmd card <command-id>
homecmd run <command-id> [key=value ...]
homecmd log <run-id>
```

ACP endpoints:

```text
GET  /health
GET  /agents
GET  /agents/homecmd-agent
POST /runs
POST /mcp   (call_worker only)
```

The ACP message content is a JSON string selecting `search`, `card`, `run`, or
`log`. MCP clients receive adapter tools including `run_agent`; they never
receive direct registry, policy, or executor access. The server implements the
synchronous inline text/JSON ACP subset used by that adapter.

Token controls retained from v0.3.0:

- Search returns no more than 20 compact command summaries.
- One card is expanded only after selection.
- ACP run responses preview at most 4,000 combined output characters.
- Full card-bounded output requires an explicit log operation.
- No custom five-tool bridge, command resource catalog, or cancel tool is added.

## Security Boundary

- Registry cards fix the executable and argument positions.
- Pydantic rejects unknown card fields and invalid templates.
- Caller-controlled interpreter source positions are invalid command cards.
- Execution uses `shell=False`, no stdin, a bounded environment, timeout, and
  output caps.
- Filesystem cards resolve beneath `HOMECMD_VAULT_ROOT`; sensitive vault output
  and write content are redacted from persistent audit records.
- Worker prompts and responses are never persisted; the worker has one fixed
  LM Studio destination and no command-core reference.
- The default policy permits only `read` risk.
- Audit JSONL redacts declared secret arguments and their output values.
- The server binds to loopback by default.
- Non-loopback binds require bearer authentication and asserted TLS termination.
- The container runs as an unprivileged user.

## VSA Layout

```text
src/homecmd/
  models.py + registry.py       command contract slice
  policy.py + executor.py       authorization/execution slice
  audit.py                      durable evidence slice
  app.py + cli.py               direct human interface slice
  acp.py + server.py            network protocol slice
  worker.py                     bounded one-tool MCP worker slice
  filesystem.py                 vault-root filesystem slice
  data/commands/core.toml       starter registry slice
configs/
  policy.*.toml                 deployment policy
  mcp-clients/                  adapter client examples
scripts/
  ci_check.py                   syntax, complexity, board, hygiene gate
  adapter_smoke.py              live ACP-MCP compatibility gate
  worker_smoke.py               live bounded LM Studio gate
  vault_smoke.py                live CLI vault round-trip gate
tests/                          focused contract tests
```

Ownership and worktree boundaries are authoritative in `manifest_slices.md`.
The active implementation worktree is `C:/Dev/projects/mcp-acp-homecmd` on
`feature/acp-homecmd`.

## Install And Operate

```powershell
python -m pip install .
homecmd search version
homecmd-agent
uvx --with acp-sdk==0.8.4 acp-mcp==0.4.2 http://127.0.0.1:8000
```

Routine verification:

```powershell
python -m pytest
python -m compileall -q src scripts tests
python scripts/ci_check.py
```

External compatibility verification:

```powershell
python scripts/adapter_smoke.py
python scripts/worker_smoke.py
python scripts/vault_smoke.py
```

## Maintenance Rules

1. Add capabilities as reviewed command cards, never as arbitrary execution.
2. Keep ACP parsing isolated in `acp.py` and adapter configuration under
   `configs/mcp-clients/`.
3. Pin both archived adapter/SDK versions and rerun the live smoke before release.
4. Keep every function at cyclomatic complexity 10 or lower.
5. Record multi-agent ownership and lifecycle in `AGENT_BOARD.jsonl`.
6. Migrate the protocol edge to A2A separately from the command core.

## Acceptance Evidence

- Unit and integration tests cover registry, policy, executor, audit, CLI, ACP,
  authentication, legacy-route absence, and CI governance.
- Package installation creates `homecmd` and `homecmd-agent` entry points.
- CLI search, card, run, and log complete against the packaged registry.
- ACP discovery and synchronous execution complete over live HTTP.
- The pinned adapter initializes over MCP stdio and exposes `run_agent`.
- Live adapter MCP `tools/call` executes `system.python_version` through ACP.
- Native worker MCP discovery exposes exactly `call_worker`, and a live call
  returns LM Studio output without persisting prompt content.
- Packaged vault cards complete write/read/list through the CLI while enforcing
  the configured root and redacted audit boundary.
