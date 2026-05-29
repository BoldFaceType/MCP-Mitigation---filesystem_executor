# MCP Activation and Discovery

Date: 2026-05-29

## Decision

Activation and discovery are split by trust boundary.

Local trusted models and agents may use a local MCP endpoint. External foundation models may use only a bounded worker endpoint that exposes one tool: `call_worker`.

## Local discovery

Local clients should connect to the local service endpoint:

```text
http://localhost:8000/mcp
```

From a container on the same Docker network, use:

```text
http://mcp-mitigation:8000/mcp
```

MCP-native discovery is performed with:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

For the bounded worker endpoint, `tools/list` returns only:

```text
call_worker
```

If a broader local control-plane MCP bridge is added later, it should use a separate local-only endpoint such as:

```text
/mcp/local
```

That local-only endpoint may expose compact command tools such as:

```text
cmd_search
cmd_card
cmd_run
cmd_log
```

Do not expose the local control-plane endpoint to external foundation models.

## External discovery

External foundation models should discover only a published or registered remote MCP endpoint that maps to the bounded worker plane:

```text
https://<secure-gateway>/mcp
```

The gateway may proxy inward to the local service, but it must expose only:

```text
call_worker
```

External model discovery remains MCP-native:

```text
tools/list -> call_worker only
tools/call -> call_worker only
```

The external model must never discover or call `homecmd`, `cmd_run`, Docker, filesystem, Git, shell, Ollama direct access, or LM Studio direct access.

## Recommended endpoint layout

```text
Local trusted clients
  -> http://localhost:8000/mcp/local
  -> cmd_search, cmd_card, cmd_run, cmd_log

External foundation models
  -> https://<secure-gateway>/mcp
  -> call_worker only

Internal worker broker
  -> LM Studio now
  -> Ollama later
```

## Activation path

1. Run or rebuild `mcp-mitigation` so `/mcp` is live.
2. Configure local MCP clients to use `http://localhost:8000/mcp`.
3. Add an authenticated gateway only when external foundation models need access.
4. Route the gateway only to the bounded worker endpoint.
5. Register the external model integration against the gateway URL, not against the local command surface.

## Boundary rule

Discovery is allowed, but the discovery result is bounded by endpoint.

External foundation models discover exactly one tool: `call_worker`.

Local trusted clients may later discover the broader command bridge, but only on a separate local-only endpoint.
