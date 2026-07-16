from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic import model_validator
from starlette.concurrency import run_in_threadpool

from .app import HomecmdService
from .executor import ArgumentValidationError
from .policy import PolicyDenied
from .registry import CommandNotFoundError


AGENT_NAME = "homecmd-agent"
ACP_OUTPUT_PREVIEW_CHARS = 4000


class MessagePart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: str
    content: str | None = None
    content_encoding: Literal["plain", "base64"] = "plain"
    name: str | None = None
    content_url: str | None = None
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_content_source(self) -> "MessagePart":
        if (self.content is None) == (self.content_url is None):
            raise ValueError("exactly one of content or content_url is required")
        return self


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parts: list[MessagePart] = Field(min_length=1)
    created_at: datetime | None = None
    completed_at: datetime | None = None
    role: str | None = Field(default=None, pattern=r"^(user|agent(?:/[A-Za-z0-9_-]+)?)$")


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    mode: Literal["sync"] = "sync"
    input: list[Message] = Field(min_length=1)
    session_id: str | None = None


def agent_manifest() -> dict[str, Any]:
    return {
        "name": AGENT_NAME,
        "description": (
            "Progressive command gateway. Send JSON with operation search, card, run, or log. "
            "Search first, inspect one card, then run only its registered command_id."
        ),
        "input_content_types": ["text/plain", "application/json"],
        "output_content_types": ["application/json"],
        "metadata": {
            "security": "registered-command-cards-only",
            "protocol_status": "legacy-acp-compatibility",
        },
    }


def parse_payload(run: RunRequest) -> dict[str, Any]:
    if run.agent_name != AGENT_NAME:
        raise HTTPException(status_code=404, detail="Agent not found.")
    part = run.input[-1].parts[-1]
    if part.content is None or part.content_encoding != "plain":
        raise HTTPException(status_code=400, detail="homecmd-agent requires inline plain JSON text.")
    if part.content_type not in {"application/json", "text/plain"}:
        raise HTTPException(status_code=400, detail="homecmd-agent accepts JSON text only.")
    try:
        payload = json.loads(part.content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON message content.") from exc
    if isinstance(payload, dict):
        return payload
    raise HTTPException(status_code=400, detail="Message content must be a JSON object.")


def dispatch(service: HomecmdService, payload: dict[str, Any]) -> Any:
    operation = payload.get("operation")
    if operation == "search":
        return service.search(str(payload.get("query", "")))
    if operation == "card":
        return service.card(str(payload.get("command_id", "")))
    if operation == "run":
        args = payload.get("args", {})
        if not isinstance(args, dict):
            raise HTTPException(status_code=400, detail="args must be an object.")
        return compact_run_result(service.run(str(payload.get("command_id", "")), args))
    if operation == "log":
        return service.log(str(payload.get("run_id", "")))
    raise HTTPException(status_code=400, detail="Unknown operation.")


def compact_run_result(result: dict[str, Any]) -> dict[str, Any]:
    compact = dict(result)
    stdout = str(compact.get("stdout", ""))
    stderr = str(compact.get("stderr", ""))
    compact["stdout"] = stdout[:ACP_OUTPUT_PREVIEW_CHARS]
    remaining = max(0, ACP_OUTPUT_PREVIEW_CHARS - len(compact["stdout"]))
    compact["stderr"] = stderr[:remaining]
    if len(stdout) + len(stderr) > ACP_OUTPUT_PREVIEW_CHARS:
        compact["truncated"] = True
    return compact


def create_acp_app(service: HomecmdService, token: str | None = None) -> FastAPI:
    app = FastAPI(title="homecmd-agent", version="0.4.0")

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        if token and request.url.path != "/health":
            provided = request.headers.get("Authorization", "")
            expected = f"Bearer {token}"
            if not secrets.compare_digest(provided, expected):
                return JSONResponse(status_code=401, content={"detail": "Unauthorized."})
        return await call_next(request)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/agents")
    async def agents() -> dict[str, list[dict[str, Any]]]:
        return {"agents": [agent_manifest()]}

    @app.get("/agents/{name}")
    async def get_agent(name: str) -> dict[str, Any]:
        if name != AGENT_NAME:
            raise HTTPException(status_code=404, detail="Agent not found.")
        return agent_manifest()

    @app.post("/runs")
    async def runs(request: Request) -> dict[str, Any]:
        try:
            run = RunRequest.model_validate(await request.json())
        except (ValidationError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid ACP run request.") from exc
        try:
            result = await run_in_threadpool(dispatch, service, parse_payload(run))
        except PolicyDenied as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ArgumentValidationError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (CommandNotFoundError, KeyError) as exc:
            raise HTTPException(status_code=404, detail="Command or run not found.") from exc
        now = datetime.now(timezone.utc).isoformat()
        return {
            "run_id": str(uuid.uuid4()),
            "agent_name": AGENT_NAME,
            "session_id": run.session_id or str(uuid.uuid4()),
            "status": "completed",
            "await_request": None,
            "output": [{
                "parts": [{
                    "name": None,
                    "content_type": "application/json",
                    "content": json.dumps(result, ensure_ascii=True, separators=(",", ":")),
                    "content_encoding": "plain",
                    "content_url": None,
                }],
                "created_at": now,
                "completed_at": now,
            }],
            "error": None,
            "created_at": now,
            "finished_at": now,
        }

    return app
