"""Kilo Code provider (Decision #119, axis-1).

Kilo (VSCode addon + CLI) is a runtime *host*, not a model vendor — the model it
runs is typically a z.ai GLM via the Anthropic-compatible endpoint, resolved
from config and looked up in model_profiles. Kilo has no Claude-style JSONL
transcript, so active-model detection reads the selected model id from, in
order: the ``KILO_MODEL`` env var, then a ``model`` field in the project/user
Kilo config under ``.kilocode/``. Returns None when nothing is set — callers
treat None as "unknown" and fall back to the model_profiles default.
"""

from __future__ import annotations

import json
import os

from . import register
from .base import Provider


class KiloProvider(Provider):
    def name(self) -> str:
        return "kilo"

    def get_transcript_path(self) -> str | None:
        return None

    def get_active_model(self) -> str | None:
        env = os.environ.get("KILO_MODEL")
        if env and env.strip():
            return env.strip()
        path = self._find_kilo_config()
        if not path or not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        model = data.get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
        return None

    def _find_kilo_config(self) -> str | None:
        env = os.environ.get("KILO_CONFIG")
        if env and os.path.isfile(env):
            return env
        for candidate in (
            os.path.join(os.getcwd(), ".kilocode", "kilo.json"),
            os.path.join(os.path.expanduser("~"), ".config", "kilo", "kilo.json"),
        ):
            if os.path.isfile(candidate):
                return candidate
        return None


def _register_self() -> None:
    register(KiloProvider())
