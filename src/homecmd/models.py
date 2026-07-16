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
SOURCE_INTERPRETERS = {
    "@python",
    "lua",
    "lua.exe",
    "node",
    "node.exe",
    "perl",
    "perl.exe",
    "php",
    "php.exe",
    "python",
    "python.exe",
    "python3",
    "python3.exe",
    "ruby",
    "ruby.exe",
}
INTERPRETER_SOURCE_OPTIONS = {"-c", "-e", "-m", "-p", "--eval", "--print"}


class ArgumentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    type: ArgumentType = "string"
    required: bool = False
    secret: bool = False
    choices: tuple[str, ...] = ()
    max_length: int | None = Field(default=None, ge=1, le=100_000)
    allow_leading_dash: bool = False


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
    sensitive_output: bool = False

    @model_validator(mode="after")
    def validate_template(self) -> "CommandCard":
        if not self.argv:
            raise ValueError("argv must contain a fixed executable")
        if _placeholder_name(self.argv[0]) is not None:
            raise ValueError("command executable must be fixed")
        executable = PurePath(self.argv[0].replace("\\", "/")).name.lower()
        if executable in SHELL_EXECUTABLES:
            raise ValueError("shell interpreters are not valid command-card executables")
        if _has_caller_controlled_interpreter_source(executable, self.argv):
            raise ValueError("caller-controlled interpreter source is not allowed")
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
        _validate_leading_dash_arguments(self.argv, self.arguments)
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


def _has_caller_controlled_interpreter_source(executable: str, argv: tuple[str, ...]) -> bool:
    if executable not in SOURCE_INTERPRETERS:
        return False
    source_follows = False
    for token in argv[1:]:
        placeholder = _placeholder_name(token)
        if source_follows:
            return placeholder is not None
        if token.lower() in INTERPRETER_SOURCE_OPTIONS:
            source_follows = True
            continue
        if token == "--" or token.startswith("-"):
            continue
        return placeholder is not None
    return False


def _validate_leading_dash_arguments(
    argv: tuple[str, ...],
    arguments: tuple[ArgumentSpec, ...],
) -> None:
    for argument in arguments:
        if not argument.allow_leading_dash:
            continue
        placeholder = f"{{{argument.name}}}"
        positions = [index for index, token in enumerate(argv) if token == placeholder]
        if not positions or any("--" not in argv[:index] for index in positions):
            raise ValueError(f"leading-dash argument requires -- before placeholder: {argument.name}")
