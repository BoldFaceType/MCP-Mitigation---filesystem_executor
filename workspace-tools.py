"""
title: Workspace Tools (MCP Mitigation)
author: metaurus
version: 1.0
requirements: requests
"""

from pydantic import BaseModel


class Tools:

    class Valves(BaseModel):
        BASE_URL: str = "http://mcp-mitigation:8000"

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def read_file(self, path: str) -> str:
        """
        Read a file from the shared workspace (/workspace).

        :param path: Relative path within the workspace (e.g. "myproject/main.py").
        :return: File contents as a string, or an error message.
        """
        import requests

        try:
            r = requests.get(
                f"{self.valves.BASE_URL}/files/read",
                params={"path": path},
                timeout=15,
            )
            r.raise_for_status()
            return r.json().get("content", "")
        except requests.exceptions.ConnectionError:
            return "Error: mcp-mitigation service is unreachable."
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            return f"Error: {detail}"
        except Exception as e:
            return f"Error: {str(e)}"

    def write_file(self, path: str, content: str) -> str:
        """
        Write (create or overwrite) a file in the shared workspace (/workspace).

        :param path: Relative path within the workspace (e.g. "myproject/notes.txt").
        :param content: Text content to write to the file.
        :return: Confirmation message or error.
        """
        import requests

        try:
            r = requests.post(
                f"{self.valves.BASE_URL}/files/write",
                json={"path": path, "content": content},
                timeout=15,
            )
            r.raise_for_status()
            return r.json().get("message", "ok")
        except requests.exceptions.ConnectionError:
            return "Error: mcp-mitigation service is unreachable."
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            return f"Error: {detail}"
        except Exception as e:
            return f"Error: {str(e)}"

    def list_directory(self, path: str = ".") -> str:
        """
        List the contents of a directory in the shared workspace (/workspace).

        :param path: Relative path within the workspace (default: root of workspace).
        :return: JSON-formatted list of entries, or an error message.
        """
        import json
        import requests

        try:
            r = requests.get(
                f"{self.valves.BASE_URL}/files/list",
                params={"path": path},
                timeout=15,
            )
            r.raise_for_status()
            entries = r.json().get("entries", [])
            return json.dumps(entries, indent=2)
        except requests.exceptions.ConnectionError:
            return "Error: mcp-mitigation service is unreachable."
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            return f"Error: {detail}"
        except Exception as e:
            return f"Error: {str(e)}"
