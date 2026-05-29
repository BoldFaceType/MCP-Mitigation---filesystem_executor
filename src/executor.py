import subprocess
import sys


_SUPPORTED = {"python", "python3", "shell", "bash", "sh"}


def execute_code(code: str, language: str = "python") -> tuple[str, str | None]:
    """
    Execute code in a subprocess and return (stdout, stderr_or_None).

    Supported languages: python / python3, shell / bash / sh
    Working directory: /workspace (mounted from host C:/Dev/projects)
    Timeout: 30 seconds
    """
    language = language.lower().strip()

    if language not in _SUPPORTED:
        return "", f"Unsupported language '{language}'. Supported: python, shell/bash/sh."

    if language in ("python", "python3"):
        cmd = [sys.executable, "-c", code]
    else:
        cmd = ["bash", "-c", code]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/workspace",
        )
        stdout = proc.stdout
        stderr = proc.stderr.strip() if proc.stderr.strip() else None

        if proc.returncode != 0:
            # Non-zero exit: return whatever stdout came out, surface stderr as error
            return stdout, stderr or f"Process exited with code {proc.returncode}"

        return stdout, None

    except subprocess.TimeoutExpired:
        return "", "Execution timed out after 30 seconds."
    except FileNotFoundError as e:
        return "", f"Interpreter not found: {e}"
    except Exception as e:
        return "", str(e)
