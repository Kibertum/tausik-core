"""Closed protected-action classifier shared by preflight issue and trusted hooks."""

from __future__ import annotations

import importlib
import ntpath
import re
import shlex
from collections.abc import Mapping

from tausik_utils import ServiceError

PROTECTED_KINDS = frozenset(
    {"framework_ui", "release_shell", "remote_operation", "commit", "push", "blocker"}
)
_MCP_PREFIXES = ("mcp__tausik-project__", "mcp__tausik_project__")
_TRUSTED_SHELL_TOOLS = frozenset({"Bash", "PowerShell", "mcp__windows-mcp__PowerShell"})
_LAUNCHER_VALUE_FLAGS = {
    "nice": frozenset({"-n", "--adjustment"}),
    "time": frozenset({"-f", "--format", "-o", "--output"}),
    "nohup": frozenset(),
}


class ProtectedActionClassificationError(ServiceError):
    code = "PROTECTED_COMMAND_AMBIGUOUS"


def _shell_vectors(command: str) -> list[list[str]]:
    """Parse direct command vectors without treating quoted command text as executable."""
    authorization = importlib.import_module("hooks.codex_cli_authorization")
    vectors: list[list[str]] = []
    for statement in authorization._shell_statements(command):
        try:
            tokens = shlex.split(statement, posix=False)
        except ValueError as exc:
            if re.search(r"(?i)\b(?:git|gh|curl|wget|ssh|scp|tausik)\b", statement):
                raise ProtectedActionClassificationError(
                    "protected shell command could not be parsed"
                ) from exc
            continue
        index = 0
        while index < len(tokens):
            token = tokens[index]
            base = ntpath.basename(token.strip("\"'")).lower().removesuffix(".exe")
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token):
                index += 1
                continue
            if base == "env":
                index += 1
                while index < len(tokens) and (
                    re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[index])
                    or tokens[index].startswith("-")
                ):
                    index += 1
                continue
            if base in {"command", "exec", "sudo", "&"}:
                index += 1
                while index < len(tokens) and tokens[index].startswith("-"):
                    index += 1
                continue
            if base in _LAUNCHER_VALUE_FLAGS:
                value_flags = _LAUNCHER_VALUE_FLAGS[base]
                index += 1
                while index < len(tokens) and tokens[index].startswith("-"):
                    option = tokens[index]
                    index += 1
                    if option in value_flags and index < len(tokens):
                        index += 1
                continue
            break
        if index < len(tokens):
            vectors.append(tokens[index:])
    return vectors


def _cmd_builtin_tail(tokens: list[str]) -> list[str]:
    """Expose commands launched through CMD's CALL and START built-ins."""
    if not tokens:
        return tokens
    builtin = tokens[0].strip("\"'").lower()
    if builtin == "call":
        return tokens[1:]
    if builtin != "start":
        return tokens
    index = 1
    if index < len(tokens) and tokens[index].startswith(('"', "'")):
        index += 1
    value_options = {"/d", "/node", "/affinity", "/machine"}
    while index < len(tokens) and tokens[index].startswith("/"):
        option = tokens[index].lower()
        index += 1
        if option in value_options and index < len(tokens):
            index += 1
    return tokens[index:]


def _strip_outer_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _shell_kind(command: str) -> str | None:
    authorization = importlib.import_module("hooks.codex_cli_authorization")
    kinds: set[str] = set()
    for cli_tokens in authorization._cli_argument_vectors(command):
        bindings = authorization._bindings(cli_tokens)
        for route, arguments in bindings:
            if route == "cli_task_mutation" and arguments.get("action") == "block":
                kinds.add("blocker")
    for tokens in _shell_vectors(command):
        executable = ntpath.basename(tokens[0].strip("\"'")).lower().removesuffix(".exe")
        args = [token.lower().strip("\"'") for token in tokens[1:]]
        # Host launchers are executable boundaries, not harmless text. Parse
        # their command tail recursively; if a protected executable is present
        # but the wrapper shape is unsupported, fail closed instead of silently
        # returning None.
        if executable in {"cmd", "powershell", "pwsh", "bash", "sh", "zsh", "dash"}:
            nested_kind = None
            flag = next(
                (i for i, token in enumerate(args) if token in {"/c", "-c", "-command"}),
                None,
            )
            if flag is not None and flag + 1 < len(args):
                nested_tokens = tokens[flag + 2 :]
                if executable == "cmd":
                    nested_tokens = _cmd_builtin_tail(nested_tokens)
                nested = _strip_outer_quotes(" ".join(nested_tokens))
                nested_kind = _shell_kind(nested)
                if nested_kind is not None:
                    kinds.add(nested_kind)
            if re.search(
                r"(?i)\b(?:git|gh|curl|wget|ssh|scp|npm|twine|invoke-webrequest|invoke-restmethod)\b",
                command,
            ) and (flag is None or flag + 1 >= len(args)):
                raise ProtectedActionClassificationError(
                    "protected executable behind an unsupported shell wrapper"
                )
        if executable == "start-process":
            raw_args = tokens[1:]
            lowered = [token.lower() for token in raw_args]
            file_path = None
            if "-filepath" in lowered:
                file_index = lowered.index("-filepath")
                if file_index + 1 < len(raw_args):
                    file_path = raw_args[file_index + 1]
            elif raw_args and not raw_args[0].startswith("-"):
                file_path = raw_args[0]
            argument_list = ""
            if "-argumentlist" in lowered:
                argument_index = lowered.index("-argumentlist")
                argument_list = " ".join(raw_args[argument_index + 1 :]).strip("\"'")
            nested = " ".join(part for part in (file_path, argument_list) if part)
            nested_kind = _shell_kind(nested)
            if nested_kind is not None:
                kinds.add(nested_kind)
            target = ntpath.basename((file_path or "").strip("\"'")).lower().removesuffix(".exe")
            if (
                target
                in {
                    "git",
                    "gh",
                    "curl",
                    "wget",
                    "ssh",
                    "scp",
                    "npm",
                    "twine",
                    "invoke-webrequest",
                    "invoke-restmethod",
                }
                and nested_kind is None
            ):
                raise ProtectedActionClassificationError(
                    "protected executable behind Start-Process could not be classified"
                )
        if executable == "git":
            index = 0
            alias_config = False
            value_options = {"-c", "-C", "--git-dir", "--work-tree", "--namespace"}
            while index < len(tokens) - 1:
                raw = tokens[index + 1]
                if raw in value_options:
                    if raw == "-c" and index + 2 < len(tokens):
                        alias_config = alias_config or tokens[index + 2].lower().startswith(
                            "alias."
                        )
                    index += 2
                    continue
                if raw.lower().startswith("-calias."):
                    alias_config = True
                    index += 1
                    continue
                if raw.startswith(("--git-dir=", "--work-tree=", "--namespace=")):
                    index += 1
                    continue
                if raw.startswith("-"):
                    index += 1
                    continue
                break
            subcommand = args[index] if index < len(args) else ""
            tail = args[index + 1 :]
            if subcommand == "push":
                kinds.add("push")
            elif subcommand == "commit":
                kinds.add("commit")
            elif (
                subcommand == "tag" and tail and not any(item in {"-l", "--list"} for item in tail)
            ):
                kinds.add("release_shell")
            elif subcommand in {"fetch", "pull", "clone", "ls-remote"}:
                kinds.add("remote_operation")
            elif subcommand == "remote" and tail[:1] == ["update"]:
                kinds.add("remote_operation")
            elif subcommand == "submodule" and tail[:1] == ["update"]:
                kinds.add("remote_operation")
            elif alias_config:
                raise ProtectedActionClassificationError(
                    "Git alias execution cannot be bound to a protected kind"
                )
        if executable in {
            "gh",
            "curl",
            "wget",
            "ssh",
            "scp",
            "invoke-webrequest",
            "iwr",
            "invoke-restmethod",
            "irm",
        }:
            kinds.add("remote_operation")
        if executable == "npm" and "publish" in args:
            kinds.add("remote_operation")
        if executable == "twine" and "upload" in args:
            kinds.add("remote_operation")
        if executable.startswith("python") and any(
            "release" in ntpath.basename(token).lower()
            or "version" in ntpath.basename(token).lower()
            for token in tokens[1:]
        ):
            kinds.add("release_shell")
        if "version" in executable and "bump" in args:
            kinds.add("release_shell")
    if len(kinds) > 1:
        raise ProtectedActionClassificationError(
            f"compound command spans protected kinds: {', '.join(sorted(kinds))}"
        )
    return next(iter(kinds), None)


def classify_action(tool_name: object, tool_input: object) -> str | None:
    """Map only trusted, observed tool identifiers into the closed protected set."""
    if not isinstance(tool_name, str) or not isinstance(tool_input, Mapping):
        return None
    route = None
    for prefix in _MCP_PREFIXES:
        if tool_name.startswith(prefix):
            route = tool_name[len(prefix) :]
            break
    if route is not None:
        if route == "tausik_task_block":
            return "blocker"
        # The execution lease is the authorization boundary for TAUSIK's own
        # MCP surface. Memory preflight must not duplicate it and turn routine
        # lifecycle calls into a multi-token protocol.
        return None
    if tool_name not in _TRUSTED_SHELL_TOOLS:
        return None
    command = tool_input.get("command")
    return _shell_kind(command) if isinstance(command, str) else None


__all__ = ["PROTECTED_KINDS", "ProtectedActionClassificationError", "classify_action"]
