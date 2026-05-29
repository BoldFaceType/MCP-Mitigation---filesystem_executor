# Changelog

## 2026-05-29

- Added bounded MCP worker-plane activation/discovery documentation for local clients and external foundation models.
- Documented the external security boundary: remote foundation models discover exactly one tool, `call_worker`, and never receive local command, shell, filesystem, Docker, Git, Ollama, or LM Studio direct access.
- Added implementation support for a minimal `/mcp` JSON-RPC endpoint with `tools/list` and `tools/call` for `call_worker`, backed by LM Studio.
