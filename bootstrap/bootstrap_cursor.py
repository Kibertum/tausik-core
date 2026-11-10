"""Cursor-specific bootstrap translations."""


def cursor_matcher(matcher: str) -> str:
    """Translate the shared Claude tool vocabulary to Cursor's native names."""
    translated: list[str] = []
    for name in matcher.split("|") if matcher else []:
        if name in {"Bash", "PowerShell"}:
            mapped = "Shell"
        elif name in {"Edit", "MultiEdit", "NotebookEdit"}:
            mapped = "Write"
        elif name.startswith("mcp__"):
            mapped = f"MCP:{name.rsplit('__', 1)[-1]}"
        elif name == "Glob":
            continue
        else:
            mapped = name
        if mapped not in translated:
            translated.append(mapped)
    if "Write" in translated and "Delete" not in translated:
        translated.append("Delete")
    return "|".join(translated)
