from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Literal, Protocol
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from .audit import AuditLog


JsonRequest = Callable[[str, dict[str, Any] | None, int], dict[str, Any]]


class CallWorkerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str = Field(min_length=1, max_length=12_000)
    context: str = Field(default="", max_length=24_000)
    worker_profile: Literal["default"] = "default"
    max_output_chars: int = Field(default=6000, ge=1, le=6000)
    timeout_seconds: int = Field(default=120, ge=1, le=120)


class CallWorkerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    worker_id: str
    run_id: str
    summary: str = ""
    result: str = ""
    truncated: bool = False
    error: str | None = None
    message: str | None = None


class BoundedWorker(Protocol):
    def call(self, request: CallWorkerRequest) -> CallWorkerResponse: ...


class LMStudioWorker:
    def __init__(
        self,
        audit: AuditLog,
        base_url: str = "http://127.0.0.1:1234/v1",
        model: str = "",
        max_input_chars: int = 24_000,
        max_output_chars: int = 6000,
        timeout_seconds: int = 120,
        request_json: JsonRequest | None = None,
    ) -> None:
        self._audit = audit
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_input_chars = max_input_chars
        self._max_output_chars = max_output_chars
        self._timeout_seconds = timeout_seconds
        self._request_json = request_json or self._http_json

    def call(self, request: CallWorkerRequest) -> CallWorkerResponse:
        task = request.task.strip()
        context = request.context.strip()
        run_id = str(uuid4())
        input_chars = len(task) + len(context)
        if not task:
            return self._error(run_id, "invalid_request", "task is required", input_chars)
        if input_chars > self._max_input_chars:
            return self._error(run_id, "input_too_large", "task plus context is too large", input_chars)
        try:
            return self._complete(run_id, task, context, input_chars, request)
        except urllib.error.URLError as exc:
            message = str(exc.reason) if exc.reason else str(exc)
            return self._error(run_id, "backend_unreachable", message, input_chars)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            return self._error(run_id, "worker_error", str(exc), input_chars)

    def _complete(
        self,
        run_id: str,
        task: str,
        context: str,
        input_chars: int,
        request: CallWorkerRequest,
    ) -> CallWorkerResponse:
        model = self._select_model()
        timeout = min(request.timeout_seconds, self._timeout_seconds)
        output_limit = min(request.max_output_chars, self._max_output_chars)
        data = self._request_json(
            "/chat/completions",
            _completion_payload(model, task, context),
            timeout,
        )
        result = str(data["choices"][0]["message"]["content"])
        truncated = len(result) > output_limit
        result = result[:output_limit]
        response = CallWorkerResponse(
            ok=True,
            worker_id="lmstudio.default",
            run_id=run_id,
            summary=result.splitlines()[0][:240] if result.strip() else "",
            result=result,
            truncated=truncated,
        )
        self._audit.record_worker(
            run_id=run_id,
            ok=True,
            model=model,
            input_chars=input_chars,
            output_chars=len(result),
            truncated=truncated,
        )
        return response

    def _select_model(self) -> str:
        if self._model:
            return self._model
        data = self._request_json("/models", None, 5)
        for item in data.get("data", []):
            model = str(item.get("id", ""))
            if model and "embedding" not in model.lower():
                return model
        raise ValueError("LM Studio returned no chat-capable model")

    def _error(self, run_id: str, code: str, message: str, input_chars: int) -> CallWorkerResponse:
        response = CallWorkerResponse(
            ok=False,
            worker_id="lmstudio.default",
            run_id=run_id,
            error=code,
            message=message,
        )
        self._audit.record_worker(
            run_id=run_id,
            ok=False,
            model=None,
            input_chars=input_chars,
            output_chars=0,
            truncated=False,
            error=code,
        )
        return response

    def _http_json(self, path: str, payload: dict[str, Any] | None, timeout: int) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"} if data else {},
            method="POST" if data else "GET",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))


def _completion_payload(model: str, task: str, context: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a bounded local worker. Use only the supplied task and context. "
                    "You have no filesystem, shell, network, Docker, Git, or credential access."
                ),
            },
            {"role": "user", "content": f"Task:\n{task}\n\nContext:\n{context or '(none)'}"},
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
    }


def install_worker_mcp(app: FastAPI, worker: BoundedWorker) -> None:
    @app.post("/mcp", response_model=None)
    async def worker_mcp(request: Request) -> dict[str, Any] | Response:
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return _rpc_error(None, -32700, "Parse error")
        result = await run_in_threadpool(handle_worker_mcp, body, worker)
        return Response(status_code=204) if result is None else result


def handle_worker_mcp(body: Any, worker: BoundedWorker) -> dict[str, Any] | None:
    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
        return _rpc_error(None, -32600, "Invalid JSON-RPC request")
    request_id = body.get("id")
    method = body.get("method")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _rpc_result(request_id, {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "mcp-mitigation-worker", "version": "0.4.0"},
            "capabilities": {"tools": {}},
        })
    if method == "tools/list":
        return _rpc_result(request_id, {"tools": [_worker_tool()]})
    if method == "tools/call":
        return _call_worker(request_id, body.get("params"), worker)
    return _rpc_error(request_id, -32601, f"Method not found: {method}")


def _call_worker(request_id: Any, params: Any, worker: BoundedWorker) -> dict[str, Any]:
    if not isinstance(params, dict) or params.get("name") != "call_worker":
        return _rpc_error(request_id, -32602, "Only call_worker is exposed")
    try:
        request = CallWorkerRequest.model_validate(params.get("arguments") or {})
    except ValidationError as exc:
        return _rpc_error(request_id, -32602, "Invalid call_worker arguments", str(exc))
    response = worker.call(request)
    return _rpc_result(request_id, {
        "content": [{"type": "text", "text": response.model_dump_json()}],
        "isError": not response.ok,
    })


def _worker_tool() -> dict[str, Any]:
    return {
        "name": "call_worker",
        "description": (
            "Delegate one bounded task to local LM Studio. No command, shell, filesystem, "
            "Docker, Git, credential, or caller-selected network access is exposed."
        ),
        "inputSchema": CallWorkerRequest.model_json_schema(),
    }


def _rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}
