"""Codex runtime provider backed by the current native session journal."""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import register
from .base import Provider

# A compacted turn_context may carry a large summary on the same JSONL line.
# Bound the read, but leave room for that one native record.
_TAIL_BYTES = 2 * 1024 * 1024


def _sessions_root() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return (
        Path(configured).expanduser() / "sessions"
        if configured
        else Path.home() / ".codex/sessions"
    )


def _current_thread() -> str | None:
    return os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")


def _model_from_tail(path: Path) -> str | None:
    """Read the latest Codex turn_context model with a bounded tail read."""
    try:
        size = path.stat().st_size
        with path.open("rb") as stream:
            stream.seek(max(0, size - _TAIL_BYTES))
            raw = stream.read()
    except OSError:
        return None
    lines = raw.decode("utf-8", errors="replace").splitlines()
    if size > _TAIL_BYTES and lines:
        lines = lines[1:]
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(row, dict) or row.get("type") != "turn_context":
            continue
        payload = row.get("payload")
        model = payload.get("model") if isinstance(payload, dict) else None
        if isinstance(model, str) and model.strip():
            return model.strip()
    return None


class CodexProvider(Provider):
    def name(self) -> str:
        return "codex"

    def get_transcript_path(self) -> str | None:
        thread = _current_thread()
        root = _sessions_root()
        if not thread or not root.is_dir():
            return None
        try:
            matches = sorted(root.glob(f"**/*{thread}.jsonl"))
        except OSError:
            return None
        return str(matches[-1]) if matches else None

    def get_active_model(self) -> str | None:
        path = self.get_transcript_path()
        return _model_from_tail(Path(path)) if path else None


def _register_self() -> None:
    register(CodexProvider())
