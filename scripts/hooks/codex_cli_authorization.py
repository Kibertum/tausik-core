"""Bounded TAUSIK CLI recognition for the Codex execution-lease hook."""

from __future__ import annotations

import fnmatch
import ntpath
import re
import shlex

_TAUSIK_CLI_HINT = re.compile(
    r"(?i)(?:^|[\s'\"(;|&!{])"
    r"(?:[^\s'\";|&(){}]*/)?(?:\.tausik/tausik(?:\.cmd)?|scripts/project\.py|project\.py|tausik(?:\.cmd)?)"
    r"(?=$|[\s'\");|&}])"
)
_TASK_MUTATIONS_WITH_SLUG = frozenset(
    {
        "block",
        "claim",
        "delete",
        "delegate",
        "depends",
        "done",
        "log",
        "move",
        "obsolete",
        "plan",
        "reason-step",
        "rename",
        "review",
        "step",
        "summary-back",
        "unblock",
        "unclaim",
        "undelegate",
        "undepends",
        "update",
    }
)


def _plain(token: str) -> str:
    return token.strip("\"'")


def _is_tausik_entrypoint(token: str) -> bool:
    normalized = _plain(token).replace("\\", "/").lower()
    return (
        normalized.endswith("/.tausik/tausik")
        or normalized.endswith("/.tausik/tausik.cmd")
        or normalized in {".tausik/tausik", ".tausik/tausik.cmd", "tausik", "tausik.cmd"}
        or normalized.endswith("/scripts/project.py")
        or normalized in {"scripts/project.py", "project.py"}
    )


def _cli_argument_vectors(command: str) -> list[list[str]]:
    """Return arguments after bounded direct or Python TAUSIK entrypoints."""
    try:
        from .python_invocation import is_python, python_script
    except ImportError:  # Standalone deployed hook: hooks directory is sys.path[0].
        from python_invocation import is_python, python_script

    invocations: list[list[str]] = []
    for statement in re.split(r"(?:\r?\n|[;&|]+)", command):
        statement = statement.strip()
        while statement.startswith("(") and statement.endswith(")"):
            statement = statement[1:-1].strip()
        try:
            tokens = [_plain(token) for token in shlex.split(statement, posix=False)]
        except ValueError as exc:
            raise ValueError(f"TAUSIK CLI arguments could not be parsed: {exc}") from exc
        if not tokens:
            continue
        entrypoint_index = 0
        while entrypoint_index < len(tokens):
            token = tokens[entrypoint_index]
            base = ntpath.basename(token).lower().removesuffix(".exe")
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token):
                entrypoint_index += 1
                continue
            if base == "env":
                entrypoint_index += 1
                while entrypoint_index < len(tokens):
                    item = tokens[entrypoint_index]
                    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", item):
                        entrypoint_index += 1
                        continue
                    if item in {"-u", "--unset", "-C", "--chdir"}:
                        entrypoint_index += 2
                        continue
                    if item in {"-S", "--split-string"}:
                        if entrypoint_index + 1 >= len(tokens):
                            entrypoint_index = len(tokens)
                            break
                        tokens = [
                            _plain(token)
                            for token in shlex.split(tokens[entrypoint_index + 1], posix=False)
                        ] + tokens[entrypoint_index + 2 :]
                        entrypoint_index = 0
                        break
                    if item.startswith("--split-string="):
                        tokens = [
                            _plain(token)
                            for token in shlex.split(item.split("=", 1)[1], posix=False)
                        ] + tokens[entrypoint_index + 1 :]
                        entrypoint_index = 0
                        break
                    if item.startswith(("--unset=", "--chdir=")) or item.startswith("-"):
                        entrypoint_index += 1
                        continue
                    break
                continue
            if base in {"command", "exec"}:
                entrypoint_index += 1
                while entrypoint_index < len(tokens) and tokens[entrypoint_index].startswith("-"):
                    entrypoint_index += 1
                continue
            break
        if entrypoint_index >= len(tokens):
            continue
        executable = ntpath.basename(tokens[entrypoint_index]).lower().removesuffix(".exe")
        if is_python(executable):
            script = python_script(tokens[entrypoint_index + 1 :])
            if script is None or not _is_tausik_entrypoint(script):
                continue
            entrypoint_index = tokens.index(script, entrypoint_index + 1)
        elif not _is_tausik_entrypoint(tokens[entrypoint_index]):
            continue
        invocations.append(tokens[entrypoint_index + 1 :])
    return invocations


def _shell_statements(command: str) -> list[str]:
    """Split control chains without treating quoted operators as boundaries."""
    statements: list[str] = []
    start = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(command):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote != "'":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in ";&|\r\n":
            statement = command[start:index].strip()
            if statement:
                statements.append(statement)
            start = index + 1
    statement = command[start:].strip()
    if statement:
        statements.append(statement)
    return statements


def _mentions_tausik_cli(command: str) -> bool:
    return bool(_TAUSIK_CLI_HINT.search(command.replace("\\", "/")))


def _dynamic_word_may_be_entrypoint(word: str) -> bool:
    normalized = word.replace("\\", "/").lower()
    if not re.search(r"[$*?\[`{]", normalized):
        return False
    pattern = re.sub(r"\$\([^)]*\)|\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*|`[^`]*`", "*", normalized)
    pattern = re.sub(r"\{[^}]*\}", "*", pattern)
    candidates = (
        "tausik",
        ".tausik/tausik",
        "./.tausik/tausik",
        "/x/.tausik/tausik",
        "scripts/project.py",
        "./scripts/project.py",
        "/x/scripts/project.py",
    )
    return any(fnmatch.fnmatch(candidate, pattern) for candidate in candidates)


def _statement_may_invoke_tausik(statement: str) -> bool:
    try:
        from .python_invocation import is_python, python_script
    except ImportError:  # Standalone deployed hook: hooks directory is sys.path[0].
        from python_invocation import is_python, python_script

    if _mentions_tausik_cli(statement):
        return True
    try:
        words = shlex.split(statement, posix=True)
    except ValueError:
        return "tausik" in statement.lower() or "project" in statement.lower()
    for index, word in enumerate(words):
        if _is_tausik_entrypoint(word) or _dynamic_word_may_be_entrypoint(word):
            return True
        executable = ntpath.basename(word).lower().removesuffix(".exe")
        if is_python(executable):
            script = python_script(words[index + 1 :])
            if script and (
                _is_tausik_entrypoint(script) or _dynamic_word_may_be_entrypoint(script)
            ):
                return True
    return False


def _has_executable_substitution(statement: str) -> bool:
    """Detect command substitution outside single quotes without executing it."""
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(statement):
        char = statement[index]
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif quote == "'":
            if char == "'":
                quote = None
        elif char == "'" and quote is None:
            quote = "'"
        elif char == '"':
            quote = None if quote == '"' else '"'
        elif (
            char == "`"
            or (char == "$" and statement[index : index + 2] == "$(")
            or (char in "<>" and statement[index : index + 2] in {"<(", ">("})
        ):
            return True
        index += 1
    return False


def _flag_value(tokens: list[str], flag: str) -> str | None:
    for index, token in enumerate(tokens):
        if token == flag and index + 1 < len(tokens):
            return tokens[index + 1]
        if token.startswith(flag + "="):
            return token.split("=", 1)[1]
    return None


def _task_start_slug(tokens: list[str]) -> str:
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token in {"--package", "--force"}:
            index += 1
            continue
        if token == "--max-bytes":
            if index + 1 >= len(tokens):
                raise ValueError("task start --max-bytes has no value")
            index += 2
            continue
        if token.startswith("--max-bytes="):
            index += 1
            continue
        if token.startswith("-"):
            raise ValueError(f"unsupported task start option: {token}")
        return token
    raise ValueError("task start has no slug")


def _bindings(tokens: list[str]) -> list[tuple[str, dict[str, object]]]:
    bindings: list[tuple[str, dict[str, object]]] = []
    if len(tokens) >= 3 and tokens[0] == "task":
        route = "cli_task_start" if tokens[1] == "start" else "cli_task_mutation"
        if tokens[1] == "start" or tokens[1] in _TASK_MUTATIONS_WITH_SLUG:
            slug = _task_start_slug(tokens) if tokens[1] == "start" else tokens[2]
            binding: dict[str, object] = {"slug": slug}
            if route == "cli_task_mutation":
                binding["action"] = tokens[1]
            bindings.append((route, binding))
        return bindings
    if len(tokens) >= 2 and tokens[:2] == ["session", "handoff"]:
        return [("cli_session_handoff", {})]
    if len(tokens) >= 3 and tokens[0] == "spec" and tokens[1] in {"link", "unlink"}:
        return [("cli_task_mutation", {"slug": tokens[2]})]
    if len(tokens) >= 5 and tokens[0] in {"adapt", "actz"} and tokens[1] in {"link", "unlink"}:
        if tokens[3] == "task":
            return [("cli_task_mutation", {"slug": tokens[4]})]
        return []
    if len(tokens) >= 2 and tokens[:2] == ["memory", "add"]:
        slug = _flag_value(tokens, "--task")
        return [("cli_task_mutation", {"slug": slug})] if slug else []
    if tokens and tokens[0] in {"decide", "dead-end", "verify"}:
        slug = _flag_value(tokens, "--task")
        if slug:
            return [("cli_task_mutation", {"slug": slug})]
        if tokens[0] == "verify":
            if _flag_value(tokens, "--story") or _flag_value(tokens, "--epic"):
                return [("cli_verify_hierarchy", {})]
            if "--tasks" in tokens or any(t.startswith("--tasks=") for t in tokens):
                return [("cli_verify_cohort", {})]
        return []
    if len(tokens) >= 2 and tokens[:2] == ["review", "record"]:
        slug = _flag_value(tokens, "--task")
        return [("cli_task_mutation", {"slug": slug})] if slug else []
    if len(tokens) >= 2 and tokens[0] == "review" and tokens[1].startswith("cohort-"):
        if tokens[1] in {"cohort-open", "cohort-status", "cohort-record", "cohort-decide"}:
            return [("tausik_review_cohort", {})]
    if len(tokens) >= 2 and tokens[:2] == ["metrics", "log-usage"]:
        slug = _flag_value(tokens, "--task-slug")
        return [("cli_task_mutation", {"slug": slug})] if slug else []
    return bindings


def cli_authorization_requests(
    command: str,
) -> tuple[list[tuple[str | None, dict[str, object]]], bool]:
    """Return every statement's authorization request or reject ambiguity."""
    requests: list[tuple[str | None, dict[str, object]]] = []
    seen = False
    for statement in _shell_statements(command):
        vectors = _cli_argument_vectors(statement)
        if vectors:
            if _has_executable_substitution(statement):
                raise ValueError("unsupported nested shell substitution in TAUSIK CLI invocation")
            seen = True
            bindings = [binding for tokens in vectors for binding in _bindings(tokens)]
            requests.extend(bindings or [(None, {})])
        elif _statement_may_invoke_tausik(statement):
            raise ValueError("unsupported TAUSIK CLI invocation shape")
    if any(route == "cli_task_start" for route, _ in requests) and len(requests) != 1:
        raise ValueError("task start must be the only TAUSIK action in a shell command")
    return requests, seen
