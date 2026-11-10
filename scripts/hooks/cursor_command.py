"""Tokenize the PowerShell command strings used by Cursor hooks."""

from __future__ import annotations


def split_cursor_command(command: str) -> list[str]:
    """Split a generated Cursor command without applying POSIX escape rules."""
    tokens: list[str] = []
    token: list[str] = []
    quote = ""
    index = 0
    while index < len(command):
        char = command[index]
        if quote:
            if char == quote:
                if quote == "'" and index + 1 < len(command) and command[index + 1] == "'":
                    token.append("'")
                    index += 2
                    continue
                quote = ""
            else:
                token.append(char)
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
        elif char.isspace():
            if token:
                tokens.append("".join(token))
                token = []
        else:
            token.append(char)
        index += 1
    if quote:
        raise ValueError("unclosed quote in Cursor hook command")
    if token:
        tokens.append("".join(token))
    return tokens
