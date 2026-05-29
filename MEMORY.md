# Project Memory

## 2026-05-29 - Bounded MCP worker-plane activation and discovery

Decisions made:

- Split MCP activation/discovery by trust boundary.
- Local trusted clients use a local MCP endpoint, initially `http://localhost:8000/mcp` or `http://mcp-mitigation:8000/mcp` from the Docker network.
- External foundation models must use an authenticated gateway endpoint that exposes only the bounded worker plane.
- External discovery uses normal MCP `tools/list`, but the result must contain exactly one tool: `call_worker`.
- The external `call_worker` path delegates bounded busy work to LM Studio now, with Ollama planned later behind the same broker contract.
- A future local control-plane bridge should be separate, for example `/mcp/local`, and may expose compact local tools such as `cmd_search`, `cmd_card`, `cmd_run`, and `cmd_log`.

Security boundary:

- External foundation models must not discover or call `homecmd`, `cmd_run`, Docker, filesystem, Git, shell, Home Assistant, Frigate, Ollama direct access, LM Studio direct access, arbitrary URL fetch, credentials, or environment access.
- Discovery is allowed only within the endpoint boundary. External endpoint discovery returns `call_worker` only.

Technical debt added:

- The existing service on port `8000` may still be an old running instance until the container/service is rebuilt or restarted.
- The local-control-plane endpoint `/mcp/local` is documented as a future split but not implemented.
- Gateway authentication and public/semi-public routing are not implemented yet.
- Ollama is documented as a future backend but is not implemented behind the worker broker yet.
- The folder `C:\Dev\projects\mcp-mitigation` is not currently a Git repository, so these changes are not tracked by Git in this directory.

## 2026-05-29 - Canonical GitHub repository promotion

Decisions made:

- `C:\Dev\projects\MCP-Mitigation---filesystem_executor` is the canonical Git checkout and SSoT for `BoldFaceType/MCP-Mitigation---filesystem_executor`.
- The recent bounded MCP worker-plane prototype from `C:\Dev\projects\mcp-mitigation` was promoted into the canonical repo.
- The canonical `main` branch was pushed directly after local hygiene, syntax, and MCP smoke verification.
- Runtime audit output remains evidence, not source; `src/audit.jsonl` is ignored and was not committed.
- The unrelated local `Google API key SKILL.md` remains untracked and out of the shipped scope.

Technical debt added:

- The non-git prototype folder still exists locally and may drift if future work continues there instead of the canonical checkout.
- Legacy local REST endpoints for execute, file access, and MQTT remain in the service alongside the bounded `/mcp` worker endpoint; deployment routing must preserve the external boundary so remote clients only reach `call_worker`.
- Gateway authentication and public/semi-public routing remain future work.
