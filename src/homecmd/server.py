from __future__ import annotations

import os

import uvicorn

from .acp import create_acp_app
from .cli import build_default_service


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_bind(host: str, token: str | None, tls_terminated: bool) -> None:
    if host not in LOOPBACK_HOSTS and not token:
        raise ValueError("A bearer token is required for a non-loopback bind.")
    if host not in LOOPBACK_HOSTS and not tls_terminated:
        raise ValueError("TLS termination is required for a non-loopback bind.")


def run_server(host: str = "127.0.0.1", port: int = 8000) -> int:
    token = os.getenv("HOMECMD_TOKEN")
    tls_terminated = os.getenv("HOMECMD_TLS_TERMINATED", "").lower() in {"1", "true", "yes"}
    validate_bind(host, token, tls_terminated)
    app = create_acp_app(build_default_service(), token=token)
    uvicorn.run(app, host=host, port=port)
    return 0


def main() -> None:
    host = os.getenv("HOMECMD_HOST", "127.0.0.1")
    port = int(os.getenv("HOMECMD_PORT", "8000"))
    raise SystemExit(run_server(host, port))


if __name__ == "__main__":
    main()
