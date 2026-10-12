"""Claude Code provider (Decision #119, axis-1).

Delegates transcript discovery + parsing to ``model_routing`` — that is the
single source of truth the tests target, so the provider must not duplicate the
parser. Because z.ai's GLM endpoint is Anthropic-compatible, a z.ai session
flows through this same path with ``model`` set to a ``glm-*`` id.
"""

from __future__ import annotations

from . import register
from .base import Provider


class ClaudeProvider(Provider):
    def name(self) -> str:
        return "claude"

    def get_transcript_path(self) -> str | None:
        try:
            from model_routing import _auto_find_transcript

            return _auto_find_transcript()
        except Exception:  # noqa: BLE001 — best-effort; missing transcript is non-fatal
            return None

    def get_active_model(self) -> str | None:
        try:
            from model_routing import read_active_model_from_transcript
        except Exception:  # noqa: BLE001
            return None
        return read_active_model_from_transcript(self.get_transcript_path())


def _register_self() -> None:
    register(ClaudeProvider())
