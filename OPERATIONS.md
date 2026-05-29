# mcp-mitigation — Operations & Maintenance

## What This Is

A FastAPI microservice that provides isolated code execution for Open-WebUI AI models.
Replaces MCP tool token overhead (~150K tokens/task) with filesystem-based code execution (~2K tokens/task).

## Service Topology

```
[Open-WebUI :3000] ──(ollama-net)──► [mcp-mitigation :8000]
                                          │
                                          └── /workspace (C:/Dev/projects mounted rw)
```

All containers run on the `ollama-net` Docker network.
Compose project: `C:/Dev/projects/ollama-webui/docker-compose.yml`

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{"status": "ok"}` |
| POST | `/execute` | Executes code; returns `{"result": "...", "error": null}` |
| GET | `/tool` | Serves `open-webui-tool.py` as plain text for URL import |

**Execute request body:**
```json
{"code": "print(1 + 1)", "language": "python"}
```

---

## Source Files

| File | Purpose | Status |
|------|---------|--------|
| `src/main.py` | FastAPI app, route definitions | Done |
| `src/executor.py` | Code execution logic | Done — subprocess sandbox, python + shell |
| `open-webui-tool.py` | Open-WebUI tool definition | Done |
| `Dockerfile` | python:3.12-slim, uvicorn with `--reload` | Done |

---

## Open-WebUI Tool Registration

**Import via URL (preferred):**
1. Open http://localhost:3000
2. Admin Panel → Workspace → Tools → **+ New Tool** → **Import from URL**
3. Enter: `http://localhost:8000/tool`
4. Click **Save**

**Or paste manually:**
1. Admin Panel → Workspace → Tools → **+ New Tool**
2. Paste full contents of `open-webui-tool.py`
3. Click **Save**

**Enable per model:**
Admin Panel → Workspace → Models → select model → Tools section → toggle **Execute Code** ON

Models with function calling support: `phi4:14b`, `qwen3.5:9b`

**Tool valve (overridable in admin panel):**
- `EXECUTE_URL` — default `http://mcp-mitigation:8000/execute`

---

## Common Operations

### Start the full stack
```bash
cd C:/Dev/projects/ollama-webui
docker compose up -d
```

### Rebuild after source changes to mcp-mitigation
```bash
cd C:/Dev/projects/ollama-webui
docker compose up -d --build mcp-mitigation
```

### Check service health
```bash
# From host
curl http://localhost:8000/health

# From open-webui container (verifies internal network)
docker exec open-webui curl -s http://mcp-mitigation:8000/health
```

### View logs
```bash
docker logs mcp-mitigation --tail 50 -f
```

### Test execute endpoint
```bash
curl -s -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "print(1+1)", "language": "python"}'
# Returns: {"result":"2\n","error":null}

# Shell example
curl -s -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "ls /workspace", "language": "shell"}'
```

---

## Verification Checklist (end-to-end)

- [ ] `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] `curl http://localhost:8000/tool` → returns Python source of open-webui-tool.py
- [ ] `POST /execute` with `{"code":"print(1+1)","language":"python"}` → `{"result":"2\n","error":null}`
- [ ] Tool imported/registered in Open-WebUI Admin Panel → Tools list
- [ ] Tool enabled on target model(s): phi4:14b, qwen3.5:9b
- [ ] Chat with model → prompt to use `execute_code` → model calls tool → actual stdout returned
