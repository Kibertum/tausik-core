"""Parse exact TAUSIK calls carried by Codex's trusted composite-tool boundary."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import re
from collections.abc import Mapping

COMPOSITE_TOOL_NAMES = frozenset({"exec", "functions.exec", "functions__exec"})
AUTHORIZATION_ARGUMENT = "_tausik_authorization"
_TOOL = r"mcp__tausik_project__(?P<route>[a-z][a-z0-9_]*)"
_DIRECT = re.compile(rf"(?<![\w$.])tools\.(?P<tool>{_TOOL})\s*\(")
_ASSIGN = re.compile(
    rf"\b(?:const|let|var)\s+(?P<alias>[A-Za-z_$][\w$]*)\s*=\s*(?<![\w$.])"
    rf"tools\.(?P<tool>{_TOOL})\b"
)
_DESTRUCTURE = re.compile(
    rf"\b(?:const|let|var)\s*\{{\s*(?P<tool>{_TOOL})"
    rf"(?:\s*:\s*(?P<alias>[A-Za-z_$][\w$]*))?\s*\}}\s*=\s*tools\b"
)
_ANY_TOOL = re.compile(_TOOL)
_IDENTIFIER = re.compile(r"[A-Za-z_$][\w$]*")
_NUMBER = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")
_MAX_CODE_BYTES = 65536
_MAX_CALLS = 32


class CompositeMcpParseError(ValueError):
    """The outer call may contain TAUSIK work but cannot be bound exactly."""


@dataclass(frozen=True)
class CompositeMcpCall:
    route: str
    arguments: dict[str, object]
    tool_name: str
    offset: int
    arguments_start: int
    arguments_end: int
    authorization: str | None = None


def composite_code(tool_name: object, tool_input: object) -> str | None:
    """Return the free-form JavaScript carried by the known Codex wrapper."""
    if tool_name not in COMPOSITE_TOOL_NAMES:
        return None
    if isinstance(tool_input, str):
        code = tool_input
    elif isinstance(tool_input, Mapping):
        values = [tool_input.get(key) for key in ("code", "input", "source", "command")]
        strings = [value for value in values if isinstance(value, str)]
        if len(strings) != 1:
            raise CompositeMcpParseError("composite tool has no unique JavaScript source")
        code = strings[0]
    else:
        raise CompositeMcpParseError("composite tool input is not text or an object")
    if len(code.encode("utf-8")) > _MAX_CODE_BYTES:
        raise CompositeMcpParseError("composite JavaScript exceeds the inspection bound")
    return code


def _mask(code: str) -> str:
    """Blank strings and comments so executable-name scans cannot read payload text."""
    out = list(code)
    index = 0
    while index < len(code):
        char = code[index]
        if char in {'"', "'", "`"}:
            quote = char
            start = index
            index += 1
            escaped = False
            while index < len(code):
                current = code[index]
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    index += 1
                    break
                index += 1
            else:
                raise CompositeMcpParseError("unterminated JavaScript string")
            if quote == "`" and "mcp__tausik_project__" in code[start:index]:
                raise CompositeMcpParseError(
                    "TAUSIK calls inside template literals are unsupported"
                )
            out[start:index] = " " * (index - start)
            continue
        if code.startswith("//", index):
            end = code.find("\n", index + 2)
            end = len(code) if end < 0 else end
            out[index:end] = " " * (end - index)
            index = end
            continue
        if code.startswith("/*", index):
            end = code.find("*/", index + 2)
            if end < 0:
                raise CompositeMcpParseError("unterminated JavaScript comment")
            end += 2
            out[index:end] = " " * (end - index)
            index = end
            continue
        index += 1
    return "".join(out)


class _LiteralParser:
    def __init__(self, source: str, start: int) -> None:
        self.source = source
        self.index = start

    def skip(self) -> None:
        while True:
            while self.index < len(self.source) and self.source[self.index].isspace():
                self.index += 1
            if self.source.startswith("//", self.index):
                end = self.source.find("\n", self.index + 2)
                self.index = len(self.source) if end < 0 else end
                continue
            if self.source.startswith("/*", self.index):
                end = self.source.find("*/", self.index + 2)
                if end < 0:
                    raise CompositeMcpParseError("unterminated JavaScript comment")
                self.index = end + 2
                continue
            return

    def value(self, depth: int = 0) -> object:
        if depth > 32:
            raise CompositeMcpParseError("JavaScript literal nesting is too deep")
        self.skip()
        if self.index >= len(self.source):
            raise CompositeMcpParseError("missing MCP arguments")
        char = self.source[self.index]
        if char == "{":
            return self.object(depth + 1)
        if char == "[":
            return self.array(depth + 1)
        if char in {'"', "'"}:
            return self.string()
        for token, value in (("true", True), ("false", False), ("null", None)):
            if self.source.startswith(token, self.index):
                end = self.index + len(token)
                if end == len(self.source) or not self.source[end].isalnum():
                    self.index = end
                    return value
        match = _NUMBER.match(self.source, self.index)
        if match:
            self.index = match.end()
            text = match.group(0)
            return float(text) if any(mark in text for mark in ".eE") else int(text)
        raise CompositeMcpParseError("MCP arguments must be static JavaScript literals")

    def string(self) -> str:
        quote = self.source[self.index]
        start = self.index
        self.index += 1
        escaped = False
        while self.index < len(self.source):
            char = self.source[self.index]
            self.index += 1
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                token = self.source[start : self.index]
                try:
                    value = json.loads(token) if quote == '"' else ast.literal_eval(token)
                except (ValueError, SyntaxError, json.JSONDecodeError) as exc:
                    raise CompositeMcpParseError("invalid JavaScript string literal") from exc
                if not isinstance(value, str):
                    raise CompositeMcpParseError("MCP string literal is not text")
                return value
        raise CompositeMcpParseError("unterminated JavaScript string")

    def object(self, depth: int) -> dict[str, object]:
        result: dict[str, object] = {}
        self.index += 1
        while True:
            self.skip()
            if self.source.startswith("}", self.index):
                self.index += 1
                return result
            if self.index < len(self.source) and self.source[self.index] in {'"', "'"}:
                key = self.string()
            else:
                match = _IDENTIFIER.match(self.source, self.index)
                if not match:
                    raise CompositeMcpParseError("MCP argument object has a dynamic key")
                key = match.group(0)
                self.index = match.end()
            self.skip()
            if not self.source.startswith(":", self.index):
                raise CompositeMcpParseError("MCP argument object uses shorthand or a method")
            self.index += 1
            if key in result:
                raise CompositeMcpParseError("MCP argument object repeats a key")
            result[key] = self.value(depth)
            self.skip()
            if self.source.startswith(",", self.index):
                self.index += 1
                continue
            if not self.source.startswith("}", self.index):
                raise CompositeMcpParseError("MCP argument object is not closed")

    def array(self, depth: int) -> list[object]:
        result: list[object] = []
        self.index += 1
        while True:
            self.skip()
            if self.source.startswith("]", self.index):
                self.index += 1
                return result
            result.append(self.value(depth))
            self.skip()
            if self.source.startswith(",", self.index):
                self.index += 1
                continue
            if not self.source.startswith("]", self.index):
                raise CompositeMcpParseError("MCP argument array is not closed")


def _arguments_at(code: str, open_paren: int) -> tuple[dict[str, object], int, int, int]:
    parser = _LiteralParser(code, open_paren + 1)
    parser.skip()
    arguments_start = parser.index
    value = parser.value()
    arguments_end = parser.index
    parser.skip()
    if parser.index >= len(code) or code[parser.index] != ")":
        raise CompositeMcpParseError("MCP call must contain exactly one literal argument object")
    if not isinstance(value, dict):
        raise CompositeMcpParseError("MCP call arguments are not an object")
    return value, parser.index + 1, arguments_start, arguments_end


def parse_composite_calls(
    tool_name: object, tool_input: object, *, accept_authorization: bool = False
) -> list[CompositeMcpCall]:
    code = composite_code(tool_name, tool_input)
    if code is None:
        return []
    masked = _mask(code)
    calls: list[CompositeMcpCall] = []
    property_offsets: set[int] = set()
    aliases: dict[str, tuple[str, str, tuple[int, int]]] = {}

    for pattern in (_ASSIGN, _DESTRUCTURE):
        for match in pattern.finditer(masked):
            alias = match.group("alias") or match.group("tool")
            if alias in aliases:
                raise CompositeMcpParseError("composite MCP alias is ambiguous")
            tool = match.group("tool")
            aliases[alias] = (
                match.group("route"),
                tool,
                match.span("alias") if match.group("alias") else match.span("tool"),
            )
            property_offsets.add(match.start("tool"))

    for match in _DIRECT.finditer(masked):
        arguments, _end, arguments_start, arguments_end = _arguments_at(code, match.end() - 1)
        authorization = arguments.pop(AUTHORIZATION_ARGUMENT, None)
        if authorization is not None and (
            not accept_authorization or not isinstance(authorization, str) or not authorization
        ):
            raise CompositeMcpParseError("model-supplied MCP authorization is forbidden")
        calls.append(
            CompositeMcpCall(
                match.group("route"),
                arguments,
                match.group("tool"),
                match.start(),
                arguments_start,
                arguments_end,
                authorization,
            )
        )
        property_offsets.add(match.start("tool"))

    for alias, (route, tool, declaration_span) in aliases.items():
        uses = list(re.finditer(rf"(?<![\w.$])\b{re.escape(alias)}\s*\(", masked))
        if not uses:
            raise CompositeMcpParseError("composite MCP alias is not called directly")
        allowed = [declaration_span]
        for use in uses:
            arguments, end, arguments_start, arguments_end = _arguments_at(code, use.end() - 1)
            authorization = arguments.pop(AUTHORIZATION_ARGUMENT, None)
            if authorization is not None and (
                not accept_authorization or not isinstance(authorization, str) or not authorization
            ):
                raise CompositeMcpParseError("model-supplied MCP authorization is forbidden")
            calls.append(
                CompositeMcpCall(
                    route,
                    arguments,
                    tool,
                    use.start(),
                    arguments_start,
                    arguments_end,
                    authorization,
                )
            )
            allowed.append((use.start(), end))
        for occurrence in re.finditer(rf"\b{re.escape(alias)}\b", masked):
            if not any(start <= occurrence.start() < end for start, end in allowed):
                raise CompositeMcpParseError("composite MCP alias escapes direct invocation")

    for match in _ANY_TOOL.finditer(masked):
        if match.start() not in property_offsets:
            raise CompositeMcpParseError("unsupported TAUSIK composite call shape")
    if "mcp__tausik_project__" in masked and not calls:
        raise CompositeMcpParseError("TAUSIK composite source contains no bound calls")
    if len(calls) > _MAX_CALLS:
        raise CompositeMcpParseError("composite contains too many TAUSIK calls")
    calls.sort(key=lambda item: item.offset)
    seen: set[tuple[str, str]] = set()
    for call in calls:
        identity = (
            call.route,
            json.dumps(call.arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )
        if identity in seen:
            raise CompositeMcpParseError("duplicate mutation identity would be ambiguous")
        seen.add(identity)
    return calls


def rewrite_composite_authorizations(
    tool_name: object,
    tool_input: object,
    calls: list[CompositeMcpCall],
    authorizations: list[str],
) -> object:
    """Inject hook-issued one-use correlations into the exact parsed calls."""

    if len(calls) != len(authorizations):
        raise CompositeMcpParseError("authorization count does not match composite calls")
    code = composite_code(tool_name, tool_input)
    if code is None:
        raise CompositeMcpParseError("composite source is missing")
    rewritten = code
    replacements = sorted(zip(calls, authorizations, strict=True), key=lambda item: item[0].offset)
    for call, authorization in reversed(replacements):
        arguments = {**call.arguments, AUTHORIZATION_ARGUMENT: authorization}
        literal = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
        rewritten = rewritten[: call.arguments_start] + literal + rewritten[call.arguments_end :]
    if isinstance(tool_input, str):
        return {"command": rewritten}
    if isinstance(tool_input, Mapping):
        result = dict(tool_input)
        source_keys = [
            key
            for key in ("code", "input", "source", "command")
            if isinstance(result.get(key), str)
        ]
        if len(source_keys) != 1:
            raise CompositeMcpParseError("composite tool has no unique JavaScript source")
        result[source_keys[0]] = rewritten
        return result
    raise CompositeMcpParseError("composite tool input is not rewritable")


__all__ = [
    "COMPOSITE_TOOL_NAMES",
    "AUTHORIZATION_ARGUMENT",
    "CompositeMcpCall",
    "CompositeMcpParseError",
    "composite_code",
    "parse_composite_calls",
    "rewrite_composite_authorizations",
]
