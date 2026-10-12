"""Kilo Code provider (Decision #119, axis-1).

Kilo (VSCode addon + CLI) is a runtime *host*, not a model vendor — the model it
runs is typically a z.ai GLM via the Anthropic-compatible endpoint, resolved
from config and looked up in model_profiles. Kilo has no Claude-style JSONL
transcript, so active-model detection reads the selected model id from, in
order:

1. ``.tausik/runtime/active_model.json`` — the LIVE observation the
   ``tausik-observe`` Kilo plugin records from the host's own chat events
   (``chat.message`` carries ``{providerID, modelID}`` of whatever provider the
   session runs: z.ai, Ollama, LM Studio, vLLM — anything). A provider-agnostic
   observation outranks static config because it is what the host is actually
   running RIGHT NOW, not what a file claims.
2. the ``KILO_MODEL`` environment variable.
3. a ``model`` field in the Kilo config — project ``.kilo/kilo.jsonc`` first
   (ours, written by bootstrap), then ``.kilocode/kilo.json`` and the user
   global ``~/.config/kilo/kilo.jsonc`` (the measured real location) with the
   legacy ``kilo.json`` spelling as fallback. Config files may be JSONC;
   parsing goes through the ONE shared reader (``jsonc_utils.load_jsonc``).

Returns None when nothing is set — callers treat None as "unknown" and fall
back to the model_profiles default. THE MODEL IS NEVER GUESSED FROM THE HOST
NAME: absence stays absence (agent_model_source doctrine).
"""

from __future__ import annotations

import json
import os

from . import register
from .base import Provider

#: The runtime observation file the tausik-observe plugin maintains. Ids only —
#: never secrets (it is a file on disk inside the project, and it is gitignored,
#: but its content is model identifiers by contract).
_RUNTIME_FILE = os.path.join(".tausik", "runtime", "active_model.json")


class KiloProvider(Provider):
    def name(self) -> str:
        return "kilo"

    def get_transcript_path(self) -> str | None:
        return None

    def get_active_model(self) -> str | None:
        observed = self._runtime_observed_model()
        if observed:
            return observed
        env = os.environ.get("KILO_MODEL")
        if env and env.strip():
            return env.strip()
        return self._model_from_config()

    def _runtime_observed_model(self) -> str | None:
        """model_id from the plugin's runtime observation, or None.

        The file is written by the host process; treat it as UNTRUSTED INPUT —
        bounded and validated through agent_model_source.sanitise, the one
        validator model ids go through before reaching the database. A missing,
        stale-shaped or invalid file is absence, never a guess and never an
        error: opening a session must survive telemetry that does not work.
        """
        path = os.path.join(os.getcwd(), _RUNTIME_FILE)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        model = data.get("model_id")
        if not isinstance(model, str) or not model.strip():
            return None
        try:
            from agent_model_source import sanitise

            return sanitise(model)
        except Exception:  # noqa: BLE001 — no validator, no value (never guess)
            return None

    def _model_from_config(self) -> str | None:
        path = self._find_kilo_config()
        if not path or not os.path.isfile(path):
            return None
        try:
            from jsonc_utils import load_jsonc

            data = load_jsonc(path)
        except Exception:  # noqa: BLE001 — an unreadable config is absence
            return None
        model = data.get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
        return None

    def _find_kilo_config(self) -> str | None:
        env = os.environ.get("KILO_CONFIG")
        if env and os.path.isfile(env):
            return env
        home = os.path.expanduser("~")
        for candidate in (
            os.path.join(os.getcwd(), ".kilo", "kilo.jsonc"),
            os.path.join(os.getcwd(), ".kilocode", "kilo.json"),
            os.path.join(home, ".config", "kilo", "kilo.jsonc"),
            os.path.join(home, ".config", "kilo", "kilo.json"),
        ):
            if os.path.isfile(candidate):
                return candidate
        return None


def _register_self() -> None:
    register(KiloProvider())
