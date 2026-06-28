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
    "qwen": {
        "config_dir": ".qwen",
        "rules_file": "QWEN.md",
        "skills_subdir": "skills",
    },
    "kilo": {
        # Kilo Code (VSCode addon + CLI). MCP config lands in .kilo/ (and the
        # Cline-lineage .kilocode/); instructions are read from AGENTS.md, which
        # bootstrap generates for every IDE.
        "config_dir": ".kilo",
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
    2. CURSOR_* / WINDSURF_* / CODEX_* env vars -> that IDE
    3. Project-structure: first matching .{ide}/ dir among
       cursor, windsurf, codex, kilo, qwen
    4. Default -> claude

    Note: kilo/qwen have no env-var branch yet — their launch-time env
    signature is unverified pending a live build (v156 P3/P5). They are
    still detected via TAUSIK_IDE and their .kilo/.qwen project dirs, which
    is reliable for a bootstrapped install.
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

    # Project-structure detection. kilo/qwen included so a Kilo-/Qwen-only
    # install resolves skill/rules paths to .kilo/.qwen instead of falling
    # back to .claude (v156 P5).
    if project_dir:
        for ide_name in ("cursor", "windsurf", "codex", "kilo", "qwen"):
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
        raise ValueError(f"Unknown IDE '{ide}', must be one of {sorted(SUPPORTED_IDES)}")
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
    """Get source skills directory in harness/, with fallback chain.

    Order: harness/skills/ (shared) -> harness/{ide}/skills/ -> harness/claude/skills/
    """
    if ide is None:
        ide = DEFAULT_IDE
    # Shared skills (preferred)
    shared = os.path.join(lib_dir, "harness", "skills")
    if os.path.isdir(shared):
        return shared
    # IDE-specific
    primary = os.path.join(lib_dir, "harness", ide, "skills")
    if os.path.isdir(primary):
        return primary
    # Fallback to claude (canonical source)
    return os.path.join(lib_dir, "harness", "claude", "skills")
