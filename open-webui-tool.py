"""
title: Execute Code (MCP Mitigation)
author: metaurus
version: 1.0
requirements: requests
"""

from pydantic import BaseModel


class Tools:

    class Valves(BaseModel):
        EXECUTE_URL: str = "http://mcp-mitigation:8000/execute"

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def execute_code(self, code: str, language: str = "python") -> str:
        """
        Execute code in an isolated server-side environment.
        Use this for tasks requiring filesystem access, network calls,
        or anything beyond pure in-browser Python.

        :param code: The code to execute.
        :param language: Programming language (default: python).
        :return: stdout output or error message from execution.
        """
        import requests

        try:
            r = requests.post(
                self.valves.EXECUTE_URL,
                json={"code": code, "language": language},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("error"):
                return f"Error: {data['error']}"
            return data["result"]
        except requests.exceptions.ConnectionError:
            return "Error: mcp-mitigation service is unreachable."
        except Exception as e:
            return f"Error: {str(e)}"
