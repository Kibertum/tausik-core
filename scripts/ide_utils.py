"""IDE abstraction layer -- detect IDE, resolve paths, provide config factory.

Centralizes all IDE-specific logic so the core framework stays IDE-agnostic.
Adding a new IDE = registering it in IDE_REGISTRY below.
"""

from __future__ import annotations

import os

# --- IDE Registry ---
# Each IDE entry: config_dir (relative to project root), rules_file, skills_subdir
IDE_REGISTRY: dict[str, dict[str, str]] = {
    "claude": {
        "config_dir": ".claude",
        "rules_file": "CLAUDE.md",
        "skills_subdir": "skills",
    },
    "cursor": {
        "config_dir": ".cursor",
        "rules_file": ".cursorrules",
        "skills_subdir": "skills",
    },
    "windsurf": {
        "config_dir": ".windsurf",
        "rules_file": ".windsurfrules",
        "skills_subdir": "skills",
    },
    "codex": {
        "config_dir": ".codex",
        "rules_file": "AGENTS.md",
        "skills_subdir": "skills",
    },
}

DEFAULT_IDE = "claude"
SUPPORTED_IDES = frozenset(IDE_REGISTRY.keys())


def detect_ide(project_dir: str | None = None) -> str:
    """Auto-detect the running IDE from environment or project structure.

    Detection order:
    1. TAUSIK_IDE environment variable (explicit override)
    2. CURSOR_* env vars -> cursor
    3. WINDSURF_* env vars -> windsurf
    4. .cursor/ dir exists in project -> cursor
    5. .windsurf/ dir exists -> windsurf
    6. Default -> claude
    """
    # Explicit override
    explicit = os.environ.get("TAUSIK_IDE", "").lower().strip()
    if explicit:
        if explicit not in SUPPORTED_IDES:
            raise ValueError(
                f"Invalid TAUSIK_IDE='{explicit}', must be one of {sorted(SUPPORTED_IDES)}"
            )
        return explicit

    # Env-based detection
    if os.environ.get("CURSOR_DIR") or os.environ.get("CURSOR_TRACE_DIR"):
        return "cursor"
    if os.environ.get("WINDSURF_DIR") or os.environ.get("WINDSURF_SESSION"):
        return "windsurf"
    if os.environ.get("CODEX_SANDBOX_DIR") or os.environ.get("OPENCODE_DIR"):
        return "codex"

    # Project-structure detection
    if project_dir:
        for ide_name in ("cursor", "windsurf", "codex"):
            config_dir = IDE_REGISTRY[ide_name]["config_dir"]
            if os.path.isdir(os.path.join(project_dir, config_dir)):
                return ide_name

    return DEFAULT_IDE


def get_ide_config(ide: str | None = None) -> dict[str, str]:
    """Get IDE configuration dict from registry.

    Raises ValueError for unknown IDE.
    """
    if ide is None:
        ide = DEFAULT_IDE
    if ide not in IDE_REGISTRY:
        raise ValueError(
            f"Unknown IDE '{ide}', must be one of {sorted(SUPPORTED_IDES)}"
        )
    return dict(IDE_REGISTRY[ide])


def get_ide_dir(project_dir: str, ide: str | None = None) -> str:
    """Get IDE-specific config directory path (e.g., .claude, .cursor)."""
    config = get_ide_config(ide)
    return os.path.join(project_dir, config["config_dir"])


def get_skills_dir(project_dir: str, ide: str | None = None) -> str:
    """Get IDE skills directory path."""
    ide_dir = get_ide_dir(project_dir, ide)
    config = get_ide_config(ide)
    return os.path.join(ide_dir, config["skills_subdir"])


def get_rules_file(project_dir: str, ide: str | None = None) -> str:
    """Get IDE rules file path (CLAUDE.md, .cursorrules, etc.)."""
    config = get_ide_config(ide)
    return os.path.join(project_dir, config["rules_file"])


def get_agents_skills_dir(lib_dir: str, ide: str | None = None) -> str:
    """Get source skills directory in agents/, with fallback chain.

    Order: agents/skills/ (shared) -> agents/{ide}/skills/ -> agents/claude/skills/
    """
    if ide is None:
        ide = DEFAULT_IDE
    # Shared skills (preferred)
    shared = os.path.join(lib_dir, "agents", "skills")
    if os.path.isdir(shared):
        return shared
    # IDE-specific
    primary = os.path.join(lib_dir, "agents", ide, "skills")
    if os.path.isdir(primary):
        return primary
    # Fallback to claude (canonical source)
    return os.path.join(lib_dir, "agents", "claude", "skills")
