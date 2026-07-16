from __future__ import annotations

from typing import Literal
from pathlib import PurePath

from pydantic import BaseModel, ConfigDict, Field, model_validator


Risk = Literal["read", "write", "destructive", "secret", "network"]
ArgumentType = Literal["string", "integer", "boolean", "path"]
SHELL_EXECUTABLES = {
    "bash",
    "cmd",
    "cmd.exe",
    "fish",
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
    "sh",
    "zsh",
}


class ArgumentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    type: ArgumentType = "string"
    required: bool = False
    secret: bool = False
    choices: tuple[str, ...] = ()


class CommandCard(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    summary: str
    risk: Risk = "read"
    argv: tuple[str, ...]
    arguments: tuple[ArgumentSpec, ...] = ()
    timeout_seconds: int = Field(default=30, ge=1, le=1800)
    max_output_chars: int = Field(default=12000, ge=1, le=1_000_000)
    working_directory: str | None = None

    @model_validator(mode="after")
    def validate_template(self) -> "CommandCard":
        if not self.argv:
            raise ValueError("argv must contain a fixed executable")
        if _placeholder_name(self.argv[0]) is not None:
            raise ValueError("command executable must be fixed")
        executable = PurePath(self.argv[0].replace("\\", "/")).name.lower()
        if executable in SHELL_EXECUTABLES:
            raise ValueError("shell interpreters are not valid command-card executables")
        argument_names = [argument.name for argument in self.arguments]
        if len(argument_names) != len(set(argument_names)):
            raise ValueError("argument names must be unique")
        defined = set(argument_names)
        referenced = {
            name
            for token in self.argv[1:]
            if (name := _placeholder_name(token)) is not None
        }
        undefined = sorted(referenced - defined)
        if undefined:
            raise ValueError(f"undefined argument placeholders: {', '.join(undefined)}")
        return self


class CommandSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    summary: str
    risk: Risk
    args: list[str] = Field(default_factory=list)


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    command_id: str
    ok: bool
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    truncated: bool = False
    error: str | None = None


def _placeholder_name(token: str) -> str | None:
    if token.startswith("{") and token.endswith("}") and token.count("{") == token.count("}") == 1:
        return token[1:-1]
    return None
