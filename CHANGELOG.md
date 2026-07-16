# Changelog

## 2026-07-16

- Fixed the pinned ACP SDK message request/response contract and verified a
  live adapter MCP `tools/call` through `run_agent`.
- Rejected caller-controlled Python and other interpreter source positions in
  command cards while preserving fixed operator code with inert arguments.
- Restored the separately bounded native MCP `call_worker` endpoint for local
  LM Studio with one-tool discovery, input/output caps, and content-free audit.
- Added root-scoped Obsidian vault read/list/write cards, atomic writes,
  explicit write policy, cross-platform absolute/path-escape rejection, and
  sensitive audit redaction.
- Added fixed read-only Git status/diff cards; kept Docker separate and omitted
  unavailable MQTT/Ollama integrations.
- Added repeatable live adapter, worker, and vault smoke gates.

## 2026-07-05

- Replaced legacy raw execution and bounded-worker deployment guidance with the ACP-first `homecmd` architecture.
- Documented human CLI, ACP `/agents` and `/runs`, and MCP compatibility through pinned `acp-mcp==0.4.2`.
- Added Codex TOML and Claude Desktop JSON MCP client examples.
- Rebuilt the Docker image to install the package and run loopback-default `homecmd-agent` without reload mode.
- Recorded the archived IBM/BeeAI ACP and `acp-mcp` boundary and A2A migration target.
- Retained v0.3.0 progressive disclosure with a 20-result search cap and 4,000-character ACP run previews.
- Pinned `acp-sdk==0.8.4` with `acp-mcp==0.4.2` after live testing found the adapter incompatible with SDK 1.0.3.
- Rejected shell-interpreter command cards, moved blocking execution off the event loop, bounded capture through temporary files, and required durable start audit records.
- Added board lease/ownership validation and a live MCP `tools/call` smoke harness.
- Recorded the v0.4.0 preview boundary: local tests pass, while live MCP
  `run_agent` execution remains blocked by an ACP request-schema mismatch.

## 2026-05-29

- Added bounded MCP worker-plane activation/discovery documentation for local clients and external foundation models.
- Documented the external security boundary: remote foundation models discover exactly one tool, `call_worker`, and never receive local command, shell, filesystem, Docker, Git, Ollama, or LM Studio direct access.
- Added implementation support for a minimal `/mcp` JSON-RPC endpoint with `tools/list` and `tools/call` for `call_worker`, backed by LM Studio.
- Promoted the bounded MCP worker-plane slice into the canonical GitHub checkout and verified `main` against `origin/main`.
