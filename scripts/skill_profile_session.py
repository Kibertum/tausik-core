"""TAUSIK skill profile session state + resolution precedence.

State file: <project>/.tausik/.session.json (auto-managed, schema-versioned).
Schema:
    {
        "schema_version": 1,
        "ide": "claude" | "cursor" | "qwen" | "codex" | null,
        "model": "opus" | "sonnet" | "gpt-5" | ... | null,
        "last_rebuild_at": "2026-05-07T..." | null,
        "source": "env" | "config" | "auto" | "unknown"
    }

Resolution precedence (highest first):
    1. TAUSIK_IDE_PROFILE  / TAUSIK_MODEL_PROFILE env vars
    2. .tausik/config.json: ide_profile / model_profile keys
    3. auto-detect via skill_profile_detect

Returned tuple: (ide, model, source). source labels the WEAKEST winning
layer — i.e. if env supplied ide and config supplied model, source is
"config" (the weaker of the two). This is the conservative default for
audit logs / debugging.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Final

_SESSION_FILENAME: Final[str] = ".session.json"
_SCHEMA_VERSION: Final[int] = 1


def _session_path(tausik_dir: str) -> str:
    return os.path.join(tausik_dir, _SESSION_FILENAME)


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "ide": None,
        "model": None,
        "last_rebuild_at": None,
        "source": "unknown",
    }


def load_session_state(tausik_dir: str) -> dict[str, Any]:
    """Read .session.json from tausik_dir. Returns defaults on missing/malformed."""
    path = _session_path(tausik_dir)
    if not os.path.isfile(path):
        return _default_state()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("session state must be an object")
        out = _default_state()
        out.update(
            {
                "ide": data.get("ide") if isinstance(data.get("ide"), str) else None,
                "model": data.get("model") if isinstance(data.get("model"), str) else None,
                "last_rebuild_at": data.get("last_rebuild_at")
                if isinstance(data.get("last_rebuild_at"), str)
                else None,
                "source": data.get("source")
                if data.get("source") in ("env", "config", "auto", "unknown")
                else "unknown",
            }
        )
        return out
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(
            f"WARN [skill_profile_session]: malformed {path}: {e} — using defaults",
            file=sys.stderr,
        )
        return _default_state()


def save_session_state(tausik_dir: str, state: dict[str, Any]) -> None:
    """Atomic write of session state. Creates tausik_dir if missing. Never raises."""
    try:
        os.makedirs(tausik_dir, exist_ok=True)
        path = _session_path(tausik_dir)
        tmp = path + ".tmp"
        out = {
            "schema_version": _SCHEMA_VERSION,
            "ide": state.get("ide"),
            "model": state.get("model"),
            "last_rebuild_at": state.get("last_rebuild_at"),
            "source": state.get("source") or "unknown",
        }
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        os.replace(tmp, path)
    except OSError as e:
        print(
            f"WARN [skill_profile_session]: write failed for {tausik_dir}: {e}",
            file=sys.stderr,
        )


def resolve_profile(
    config: dict[str, Any] | None = None,
) -> tuple[str | None, str | None, str]:
    """Resolve (ide, model, source) via precedence chain.

    Source labels the weakest layer that contributed a non-None value.
    If both layers are None, source = "unknown".
    """
    from skill_profile_detect import (
        VALID_IDES,
        VALID_MODELS,
        detect_ide,
        detect_model,
        normalize_model_profile_slug,
    )

    cfg = config or {}

    env_ide = os.environ.get("TAUSIK_IDE_PROFILE", "").strip()
    env_model = os.environ.get("TAUSIK_MODEL_PROFILE", "").strip()
    cfg_ide = str(cfg.get("ide_profile") or "").strip()
    cfg_model = str(cfg.get("model_profile") or "").strip()

    sources: list[str] = []
    ide: str | None
    model: str | None

    if env_ide:
        slug = normalize_model_profile_slug(env_ide)
        ide = slug if slug in VALID_IDES else None
        if ide:
            sources.append("env")
    elif cfg_ide:
        slug = normalize_model_profile_slug(cfg_ide)
        ide = slug if slug in VALID_IDES else None
        if ide:
            sources.append("config")
    else:
        ide = detect_ide()
        if ide:
            sources.append("auto")

    if env_model:
        slug = normalize_model_profile_slug(env_model)
        model = slug if slug in VALID_MODELS else None
        if model:
            sources.append("env")
    elif cfg_model:
        slug = normalize_model_profile_slug(cfg_model)
        model = slug if slug in VALID_MODELS else None
        if model:
            sources.append("config")
    else:
        model = detect_model()
        if model:
            sources.append("auto")

    if not sources:
        source = "unknown"
    else:
        priority = {"auto": 0, "config": 1, "env": 2}
        weakest = min(sources, key=lambda s: priority[s])
        source = weakest

    return ide, model, source


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
