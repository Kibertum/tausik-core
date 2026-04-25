"""TAUSIK config loader — find .tausik/ dir, create service, gates config."""

from __future__ import annotations

import json
import logging
import os
import re

from project_backend import SQLiteBackend
from project_service import ProjectService

logger = logging.getLogger(__name__)

# Data lives in .tausik/ (IDE-agnostic)
TAUSIK_DIR = ".tausik"
DB_NAME = "tausik.db"
CONFIG_NAME = "config.json"

# --- Gate defaults ---

VALID_GATE_SEVERITIES = frozenset({"warn", "block"})
VALID_GATE_TRIGGERS = frozenset({"task-done", "commit", "review"})

# --- Security: allowed executables for custom gates ---
ALLOWED_GATE_EXECUTABLES = frozenset(
    {
        "pytest",
        "ruff",
        "mypy",
        "bandit",
        "tsc",
        "eslint",
        "go",
        "golangci-lint",
        "cargo",
        "clippy",
        "phpstan",
        "phpcs",
        "javac",
        "ktlint",
        "npm",
        "npx",
        "pnpm",
        "yarn",
        "make",
        "python",
        "ruby",
        "php",
    }
)

# Shell operators forbidden in commands that use {files} placeholder
_SHELL_INJECTION_PATTERN = re.compile(r"\||\&\&|\|\||;|\$\(|`")

# --- SENAR Rule 9.2: Session duration limit (minutes) ---
# SENAR v1.3: sessions exceeding 180 min show diminishing returns
DEFAULT_SESSION_MAX_MINUTES = 180

DEFAULT_GATES: dict[str, dict] = {
    "pytest": {
        "enabled": True,
        "severity": "block",
        "trigger": ["task-done", "review"],
        # SENAR Rule 5: scoped to relevant_files via {test_files_for_files}
        # substitution. Falls back to full `tests/` when no test files map
        # from relevant_files (regression-safe).
        "command": "pytest -x -q {test_files_for_files}",
        "description": "Run pytest scoped to task's relevant_files",
        "timeout": 180,
    },
    "ruff": {
        "enabled": True,
        "severity": "block",
        "trigger": ["commit"],
        "command": "ruff check {files}",
        "description": "Lint with ruff before commit",
        "file_extensions": [".py"],
    },
    "mypy": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "mypy {files}",
        "description": "Type-check with mypy before commit",
        "file_extensions": [".py"],
    },
    "filesize": {
        "enabled": True,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": None,
        "description": "Warn if files exceed max_lines threshold",
        "max_lines": 400,
    },
    "bandit": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["review"],
        "command": "bandit -r {files} -q",
        "description": "Security scan with bandit",
    },
    # TypeScript / JavaScript gates
    "tsc": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": "npx tsc --noEmit 2>&1 | head -20",
        "description": "TypeScript type-check",
        "stacks": ["typescript", "react", "next", "vue", "nuxt", "svelte"],
    },
    "eslint": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "npx eslint {files} --max-warnings 0 2>&1 | head -20",
        "description": "ESLint check",
        "stacks": [
            "typescript",
            "javascript",
            "react",
            "next",
            "vue",
            "nuxt",
            "svelte",
        ],
    },
    # Go gates
    "go-vet": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": "go vet ./... 2>&1 | head -20",
        "description": "Go vet static analysis",
        "stacks": ["go"],
    },
    "golangci-lint": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "golangci-lint run {files} 2>&1 | head -20",
        "description": "Go linter suite",
        "stacks": ["go"],
    },
    # Rust gates
    "cargo-check": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": "cargo check 2>&1 | head -20",
        "description": "Rust compilation check",
        "stacks": ["rust"],
    },
    "clippy": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "cargo clippy — -D warnings 2>&1 | head -20",
        "description": "Rust linter",
        "stacks": ["rust"],
    },
    # PHP gates
    "phpstan": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": "vendor/bin/phpstan analyse {files} --no-progress 2>&1 | head -20",
        "description": "PHP static analysis",
        "stacks": ["php", "laravel"],
    },
    "phpcs": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "vendor/bin/phpcs {files} 2>&1 | head -20",
        "description": "PHP code style check",
        "stacks": ["php", "laravel"],
    },
    # Java / Kotlin gates
    "javac": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done"],
        "command": "mvn compile -q 2>&1 | head -20",
        "description": "Java compilation check",
        "stacks": ["java"],
    },
    "ktlint": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "ktlint {files} 2>&1 | head -20",
        "description": "Kotlin code style check",
        "stacks": ["kotlin"],
    },
    # TDD enforcement gate
    "tdd_order": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["task-done"],
        "command": None,
        "description": "Verify test files were modified (TDD enforcement)",
    },
}


def _build_stack_gate_map() -> dict[str, list[str]]:
    """Build mapping: stack -> list of gates to auto-enable."""
    result: dict[str, list[str]] = {}
    for gate_name, gate_cfg in DEFAULT_GATES.items():
        for stack in gate_cfg.get("stacks", []):
            result.setdefault(stack, []).append(gate_name)
    return result


STACK_GATE_MAP: dict[str, list[str]] = _build_stack_gate_map()


def auto_enable_gates_for_stacks(cfg: dict, stacks: list[str]) -> list[str]:
    """Auto-enable gates for detected stacks. Returns list of newly enabled gate names.

    Only enables gates that are not already explicitly configured by the user.
    Writes changes to config under "gates" key.
    """
    user_gates = cfg.setdefault("gates", {})
    newly_enabled: list[str] = []
    for stack in stacks:
        for gate_name in STACK_GATE_MAP.get(stack, []):
            # Skip if user already configured this gate explicitly
            if gate_name in user_gates:
                continue
            user_gates[gate_name] = {"enabled": True}
            newly_enabled.append(gate_name)
    return list(dict.fromkeys(newly_enabled))  # deduplicate preserving order


def _validate_custom_gate(name: str, gate: dict) -> str | None:
    """Validate a custom gate command for security.

    Returns None if valid, or an error message string if invalid.
    """
    command = gate.get("command")
    if not command or command is None:
        return None  # no command = built-in gate like filesize, OK

    # Extract first token (the executable)
    first_token = command.split()[0] if command.strip() else ""
    # Strip path prefixes (e.g. "vendor/bin/phpstan" -> "phpstan")
    exe = first_token.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]

    if exe not in ALLOWED_GATE_EXECUTABLES:
        return (
            f"Custom gate '{name}': executable '{exe}' not in allowed list. "
            f"Allowed: {sorted(ALLOWED_GATE_EXECUTABLES)}"
        )

    # Check for shell injection when {files} is used
    if "{files}" in command and _SHELL_INJECTION_PATTERN.search(command):
        return (
            f"Custom gate '{name}': command contains shell operators "
            f"with {{files}} placeholder — potential injection risk."
        )

    return None


def find_tausik_dir() -> str:
    """Find .tausik/ directory, searching up from cwd. Env override: TAUSIK_DIR."""
    override = os.environ.get("TAUSIK_DIR")
    if override:
        return override
    d = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(d, TAUSIK_DIR)
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    # Default to cwd
    return os.path.join(os.getcwd(), TAUSIK_DIR)


def get_db_path() -> str:
    return os.path.join(find_tausik_dir(), DB_NAME)


def get_config_path() -> str:
    return os.path.join(find_tausik_dir(), CONFIG_NAME)


def load_config() -> dict:
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logging.getLogger("tausik.config").warning(
                "Config corrupted (%s): %s — using defaults", path, e
            )
    return {}


def save_config(cfg: dict) -> None:
    """Persist config.json atomically: write to .tmp + os.replace.

    Atomicity guards against partial writes if the process is killed mid-write.
    """
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_gates(cfg: dict | None = None) -> dict[str, dict]:
    """Load gates config: merge user overrides on top of defaults.

    Returns dict of gate_name -> gate_config.
    User can override any field per gate in config.json under "gates" key.
    """
    if cfg is None:
        cfg = load_config()
    user_gates = cfg.get("gates", {})
    merged: dict[str, dict] = {}
    # Start with defaults
    for name, defaults in DEFAULT_GATES.items():
        gate = dict(defaults)
        if name in user_gates:
            gate.update(user_gates[name])
        merged[name] = gate
    # Add custom user gates (not in defaults) — with security validation
    for name, ucfg in user_gates.items():
        if name not in merged:
            error = _validate_custom_gate(name, ucfg)
            if error:
                logger.warning("Skipping gate: %s", error)
                continue
            merged[name] = ucfg
    return merged


def get_gates_for_trigger(trigger: str, cfg: dict | None = None) -> list[dict]:
    """Return enabled gates matching a specific trigger.

    Each returned dict includes a 'name' key.
    """
    all_gates = load_gates(cfg)
    result = []
    for name, gate in all_gates.items():
        if not gate.get("enabled", True):
            continue
        triggers = gate.get("trigger", [])
        if trigger in triggers:
            result.append({**gate, "name": name})
    return result


def get_service() -> ProjectService:
    """Create ProjectService with SQLite backend."""
    db_path = get_db_path()
    be = SQLiteBackend(db_path)
    return ProjectService(be)
