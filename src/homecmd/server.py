from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from .acp import create_acp_app
from .cli import build_default_service
from .worker import BoundedWorker, LMStudioWorker, install_worker_mcp


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_bind(host: str, token: str | None, tls_terminated: bool) -> None:
    if host not in LOOPBACK_HOSTS and not token:
        raise ValueError("A bearer token is required for a non-loopback bind.")
    if host not in LOOPBACK_HOSTS and not tls_terminated:
        raise ValueError("TLS termination is required for a non-loopback bind.")


def create_server_app(
    *,
    token: str | None = None,
    worker: BoundedWorker | None = None,
    audit_path: Path | None = None,
) -> FastAPI:
    service = build_default_service(audit_path=audit_path)
    app = create_acp_app(service, token=token)
    active_worker = worker or LMStudioWorker(
        audit=service.audit,
        base_url=os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1"),
        model=os.getenv("LMSTUDIO_MODEL", ""),
        max_input_chars=int(os.getenv("WORKER_MAX_INPUT_CHARS", "24000")),
        max_output_chars=int(os.getenv("WORKER_MAX_OUTPUT_CHARS", "6000")),
        timeout_seconds=int(os.getenv("WORKER_TIMEOUT_SECONDS", "120")),
    )
    install_worker_mcp(app, active_worker)
    return app


def run_server(host: str = "127.0.0.1", port: int = 8000) -> int:
    token = os.getenv("HOMECMD_TOKEN")
    tls_terminated = os.getenv("HOMECMD_TLS_TERMINATED", "").lower() in {"1", "true", "yes"}
    validate_bind(host, token, tls_terminated)
    app = create_server_app(token=token)
    uvicorn.run(app, host=host, port=port)
    return 0


def main() -> None:
    host = os.getenv("HOMECMD_HOST", "127.0.0.1")
    port = int(os.getenv("HOMECMD_PORT", "8000"))
    raise SystemExit(run_server(host, port))


if __name__ == "__main__":
    main()
