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
        # IaC tooling — added when stack-iac-vertical introduced default gates
        # (HIGH-1 review fix: without this, user overrides like
        # vendor/bin/ansible-lint silently fail _validate_custom_gate).
        "ansible-lint",
        "ansible",
        "terraform",
        "tflint",
        "tofu",
        "helm",
        "kubeval",
        "kube-score",
        "hadolint",
    }
)

# Shell operators forbidden in commands that use {files} placeholder
# (broader rule because file paths are user-controlled in {files}).
_SHELL_INJECTION_PATTERN = re.compile(r"\||\&\&|\|\||;|\$\(|`")

# Shell chain/substitution operators that are NEVER acceptable in custom
# gates regardless of {files} — legitimate static gates may pipe stdout
# to head/tail (single `|`), but command chaining (&&, ||, ;) and
# command-substitution ($(, backtick) signal an attempt to escape the
# allowed-executable whitelist. HIGH-2 review fix.
_SHELL_CHAIN_PATTERN = re.compile(r"&&|\|\||;|\$\(|`")

# --- SENAR Rule 9.2: Session duration limit (minutes) ---
# SENAR v1.3: sessions exceeding 180 min show diminishing returns
DEFAULT_SESSION_MAX_MINUTES = 180

# --- Agent-native session capacity (tool calls, not minutes) ---
DEFAULT_SESSION_CAPACITY_CALLS = 200

from default_gates import DEFAULT_GATES  # noqa: E402


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
    HIGH-2 review fix: shell metachars are blocked unconditionally now —
    previously the guard required `{files}` placeholder, which let a
    custom gate run pipelines under shell=True without scrutiny.
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

    # Always reject command chaining / substitution — these escape the
    # allowed-executable whitelist regardless of placeholder usage.
    if _SHELL_CHAIN_PATTERN.search(command):
        return (
            f"Custom gate '{name}': command contains shell operators "
            f"(&&/||/;/$(/`) — refused. Use a wrapper script or split "
            f"into multiple gates."
        )

    # Stricter rule when the user-controlled {files} placeholder is in
    # play: block bare pipes too, since they let user input redirect
    # to an arbitrary downstream command.
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
