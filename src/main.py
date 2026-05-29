import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from executor import execute_code

app = FastAPI(title="MCP Mitigation Service", version="0.2.0")

_WORKSPACE = Path("/workspace")
_TOOL_EXECUTE = Path("/app/open-webui-tool.py")
_TOOL_WORKSPACE = Path("/app/workspace-tools.py")
_TOOL_MQTT = Path("/app/mqtt-tools.py")
_AUDIT_LOG = Path(os.getenv("MCP_AUDIT_LOG", "audit.jsonl"))

_LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1").rstrip("/")
_LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "")
_WORKER_MAX_INPUT_CHARS = int(os.getenv("WORKER_MAX_INPUT_CHARS", "24000"))
_WORKER_MAX_OUTPUT_CHARS = int(os.getenv("WORKER_MAX_OUTPUT_CHARS", "6000"))
_WORKER_TIMEOUT_SECONDS = int(os.getenv("WORKER_TIMEOUT_SECONDS", "120"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_path(rel: str) -> Path:
    """Resolve a relative path inside /workspace; raise 400 on traversal."""
    resolved = (_WORKSPACE / rel).resolve()
    try:
        resolved.relative_to(_WORKSPACE.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path escapes workspace.")
    return resolved


def _audit(event: dict[str, Any]) -> None:
    event = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event}
    with _AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, separators=(",", ":")) + "\n")


def _json_rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _json_rpc_error(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _lmstudio_request(path: str, payload: dict[str, Any] | None = None, timeout: int = 10) -> dict[str, Any]:
    url = f"{_LMSTUDIO_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _select_lmstudio_model() -> str:
    if _LMSTUDIO_MODEL:
        return _LMSTUDIO_MODEL

    data = _lmstudio_request("/models", timeout=5)
    models = data.get("data", [])
    for model in models:
        model_id = str(model.get("id", ""))
        if model_id and "embedding" not in model_id.lower():
            return model_id
    raise RuntimeError("LM Studio returned no chat-capable model candidates.")


def _call_lmstudio_worker(req: "CallWorkerRequest") -> "CallWorkerResponse":
    task = req.task.strip()
    context = req.context.strip()
    requested_timeout = min(max(req.timeout_seconds, 1), _WORKER_TIMEOUT_SECONDS)
    requested_max_output = min(max(req.max_output_chars, 1), _WORKER_MAX_OUTPUT_CHARS)
    combined_input = f"{task}\n\n{context}"

    run_id = time.strftime("%Y-%m-%dT%H-%M-%SZ-worker", time.gmtime())
    if not task:
        return CallWorkerResponse(
            ok=False,
            worker_id="lmstudio.default",
            run_id=run_id,
            error="invalid_request",
            message="task is required.",
        )
    if len(combined_input) > _WORKER_MAX_INPUT_CHARS:
        return CallWorkerResponse(
            ok=False,
            worker_id="lmstudio.default",
            run_id=run_id,
            error="input_too_large",
            message=f"task plus context exceeds {_WORKER_MAX_INPUT_CHARS} characters.",
        )

    try:
        model = _select_lmstudio_model()
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a bounded local worker. Use only the task and context supplied. "
                        "Do not claim filesystem, shell, network, Docker, Git, or credential access. "
                        "Return concise, task-focused output."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Task:\n{task}\n\nContext:\n{context or '(none)'}",
                },
            ],
            "temperature": 0.2,
            "max_tokens": 1024,
        }
        data = _lmstudio_request("/chat/completions", payload=payload, timeout=requested_timeout)
        result = data["choices"][0]["message"]["content"]
        truncated = len(result) > requested_max_output
        if truncated:
            result = result[:requested_max_output]

        response = CallWorkerResponse(
            ok=True,
            worker_id="lmstudio.default",
            run_id=run_id,
            summary=result.splitlines()[0][:240] if result.strip() else "",
            result=result,
            truncated=truncated,
        )
        _audit({
            "event": "call_worker",
            "run_id": run_id,
            "ok": True,
            "backend": "lmstudio",
            "model": model,
            "input_chars": len(combined_input),
            "output_chars": len(result),
            "truncated": truncated,
        })
        return response
    except urllib.error.URLError as e:
        message = str(e.reason) if getattr(e, "reason", None) else str(e)
        response = CallWorkerResponse(
            ok=False,
            worker_id="lmstudio.default",
            run_id=run_id,
            error="backend_unreachable",
            message=message,
        )
    except Exception as e:
        response = CallWorkerResponse(
            ok=False,
            worker_id="lmstudio.default",
            run_id=run_id,
            error="worker_error",
            message=str(e),
        )

    _audit({
        "event": "call_worker",
        "run_id": run_id,
        "ok": False,
        "backend": "lmstudio",
        "error": response.error,
        "message": response.message,
        "input_chars": len(combined_input),
    })
    return response


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ExecuteRequest(BaseModel):
    code: str
    language: str = "python"


class ExecuteResponse(BaseModel):
    result: str
    error: str | None = None


class WriteRequest(BaseModel):
    path: str
    content: str


class MqttPublishRequest(BaseModel):
    host: str
    port: int = 1883
    user: str = ""
    password: str = ""
    topic: str
    payload: str
    retain: bool = False


class MqttReadRequest(BaseModel):
    host: str
    port: int = 1883
    user: str = ""
    password: str = ""
    topic: str
    timeout: int = 5


class CallWorkerRequest(BaseModel):
    task: str
    context: str = ""
    worker_profile: str = "default"
    max_output_chars: int = 6000
    timeout_seconds: int = 120


class CallWorkerResponse(BaseModel):
    ok: bool
    worker_id: str
    run_id: str
    summary: str = ""
    result: str = ""
    truncated: bool = False
    error: str | None = None
    message: str | None = None


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest) -> ExecuteResponse:
    result, error = execute_code(req.code, req.language)
    return ExecuteResponse(result=result, error=error)


@app.post("/mcp")
async def mcp_rpc(request: Request):
    body = await request.json()
    request_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}

    if body.get("jsonrpc") != "2.0":
        return _json_rpc_error(request_id, -32600, "Invalid JSON-RPC request.")

    if method == "initialize":
        return _json_rpc_result(request_id, {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "mcp-mitigation-worker", "version": "0.1.0"},
            "capabilities": {"tools": {}},
        })

    if method == "tools/list":
        return _json_rpc_result(request_id, {
            "tools": [
                {
                    "name": "call_worker",
                    "description": "Delegate one bounded task to the local LM Studio worker. No command, shell, filesystem, Docker, Git, or network access is exposed.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string"},
                            "context": {"type": "string"},
                            "worker_profile": {"type": "string", "default": "default"},
                            "max_output_chars": {"type": "integer", "default": 6000},
                            "timeout_seconds": {"type": "integer", "default": 120},
                        },
                        "required": ["task"],
                        "additionalProperties": False,
                    },
                }
            ]
        })

    if method == "tools/call":
        tool_name = params.get("name")
        if tool_name != "call_worker":
            return _json_rpc_error(request_id, -32602, "Only call_worker is exposed by this bounded MCP endpoint.")
        try:
            req = CallWorkerRequest(**(params.get("arguments") or {}))
        except Exception as e:
            return _json_rpc_error(request_id, -32602, "Invalid call_worker arguments.", str(e))
        worker_response = _call_lmstudio_worker(req)
        return _json_rpc_result(request_id, {
            "content": [
                {
                    "type": "text",
                    "text": worker_response.model_dump_json(),
                }
            ],
            "isError": not worker_response.ok,
        })

    return _json_rpc_error(request_id, -32601, f"Method not found: {method}")


# ---------------------------------------------------------------------------
# Tool-file serving
# ---------------------------------------------------------------------------

@app.get("/tool", response_class=PlainTextResponse)
async def get_tool_execute():
    """Serve the execute-code Open-WebUI tool file."""
    if not _TOOL_EXECUTE.exists():
        raise HTTPException(status_code=404, detail="Tool file not found.")
    return _TOOL_EXECUTE.read_text()


@app.get("/tool/workspace", response_class=PlainTextResponse)
async def get_tool_workspace():
    """Serve workspace-tools.py for import in the Open-WebUI admin panel."""
    if not _TOOL_WORKSPACE.exists():
        raise HTTPException(status_code=404, detail="Tool file not found.")
    return _TOOL_WORKSPACE.read_text()


@app.get("/tool/mqtt", response_class=PlainTextResponse)
async def get_tool_mqtt():
    """Serve mqtt-tools.py for import in the Open-WebUI admin panel."""
    if not _TOOL_MQTT.exists():
        raise HTTPException(status_code=404, detail="Tool file not found.")
    return _TOOL_MQTT.read_text()


# ---------------------------------------------------------------------------
# File I/O endpoints
# ---------------------------------------------------------------------------

@app.get("/files/read")
async def files_read(path: str = Query(..., description="Relative path within /workspace")):
    target = _safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if not target.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")
    return {"content": target.read_text(errors="replace")}


@app.post("/files/write")
async def files_write(req: WriteRequest):
    target = _safe_path(req.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content)
    return {"message": f"Written: {req.path}"}


@app.get("/files/list")
async def files_list(path: str = Query(".", description="Relative path within /workspace")):
    target = _safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {path}")
    entries = []
    for item in sorted(target.iterdir()):
        entries.append({
            "name": item.name,
            "type": "dir" if item.is_dir() else "file",
        })
    return {"entries": entries}


# ---------------------------------------------------------------------------
# MQTT endpoints
# ---------------------------------------------------------------------------

@app.post("/mqtt/publish")
async def mqtt_publish(req: MqttPublishRequest):
    try:
        import paho.mqtt.client as mqtt
        import paho.mqtt.publish as publish

        auth = {"username": req.user, "password": req.password} if req.user else None
        publish.single(
            req.topic,
            payload=req.payload,
            retain=req.retain,
            hostname=req.host,
            port=req.port,
            auth=auth,
        )
        return {"message": f"Published to '{req.topic}'."}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MQTT error: {str(e)}")


@app.post("/mqtt/read")
async def mqtt_read(req: MqttReadRequest):
    try:
        import threading
        import paho.mqtt.client as mqtt

        received: list = []
        event = threading.Event()

        def on_connect(client, userdata, flags, rc, properties=None):
            client.subscribe(req.topic)

        def on_message(client, userdata, msg):
            received.append(msg.payload.decode(errors="replace"))
            event.set()

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if req.user:
            client.username_pw_set(req.user, req.password)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(req.host, req.port, keepalive=10)
        client.loop_start()
        got_message = event.wait(timeout=req.timeout)
        client.loop_stop()
        client.disconnect()

        if not got_message:
            return {"timed_out": True, "payload": None}
        return {"timed_out": False, "payload": received[0]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MQTT error: {str(e)}")
