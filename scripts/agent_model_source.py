"""Where the name of the model running this session comes from.

session-model-recorded-on-non-claude-hosts. Measured on this project's own
database in session #231, before anything was designed:

    sessions:  231 rows, model_id set on 0 of them
    tasks:    1560 rows, started_model_id set on 0, done_model_id on 0,
              model_mismatch raised 0 times

So RENAR Rule 10.13 model pinning had never fired — not on GLM, which is what
the task was raised about, but not on Claude either, and not once in the
project's whole history. `session_start` consulted only environment variables
(`TAUSIK_AGENT_MODEL`, `CLAUDE_MODEL`, `ANTHROPIC_MODEL`, `OPENAI_MODEL`,
`CURSOR_MODEL`). Claude Code exports none of them and nobody sets them by hand,
so `sessions.model_id` was always NULL — and from there the rest collapsed on its
own: `model_start_updates` reads the session's model, got NULL, and pinned NULL.

THE SEAM ALREADY EXISTED AND WORKED. `providers.get('claude').get_active_model()`
was called in that same session and returned `claude-opus-5`, read from the
transcript. Every provider declares the method. `session_start` simply did not
know about it.

THE MODEL IS NEVER INFERRED FROM THE HOST. Claude Code pointed at z.ai through
`ANTHROPIC_BASE_URL` is running GLM, not Claude, and that is precisely the case
this must tell apart. A provider whose own source is silent yields ABSENCE; it
does not get to answer "probably claude-something" because of its name.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

#: Priority order, highest first. The names are read here and NOWHERE else, so
#: "which variable wins" is answerable by reading one tuple.
#:
#: `TAUSIK_AGENT_MODEL` is first because it is the deliberate override: a user
#: who states the model outranks anything guessed from the environment.
ENV_SOURCES: tuple[str, ...] = (
    "TAUSIK_AGENT_MODEL",
    "CLAUDE_MODEL",
    "ANTHROPIC_MODEL",
    "OPENAI_MODEL",
    "CURSOR_MODEL",
)

#: The variable a host that reports nothing should be told to set. Named in the
#: doctor line, so the reader is given the way out rather than a complaint.
DECLARE_WITH = "TAUSIK_AGENT_MODEL"

#: A model id is a short machine token. This is UNTRUSTED INPUT — it arrives from
#: the environment and from a file on disk, and it lands in the database and in
#: reports — so it is bounded before it travels. A megabyte of text or an escape
#: sequence reaching a terminal report is the threat here, not code execution.
#: "Not supplied" and "explicitly no host" are DIFFERENT arguments, and a plain
#: default of None cannot tell them apart — the caller who means "do not ask any
#: provider" would silently get auto-detection instead. That confusion between an
#: absent value and a default is the one this whole area exists to end, so the
#: sentinel is not ceremony.
AUTO = "<auto-detect>"

_MAX_LEN = 120
_ALLOWED = re.compile(r"^[A-Za-z0-9._:@/+-]+$")


def sanitise(raw: object) -> str | None:
    """A model id, or None when the value is empty, oversized or not a token.

    Blank and whitespace are ABSENCE, not a name: a variable set to "" is a
    variable that says nothing, and storing it would put an empty string where
    every consumer tests for None.
    """
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value or len(value) > _MAX_LEN:
        return None
    return value if _ALLOWED.match(value) else None


def from_env(environ: Mapping[str, str] | None = None) -> tuple[str | None, str | None]:
    """(model_id, source_name) from the environment, or (None, None)."""
    env = os.environ if environ is None else environ
    for name in ENV_SOURCES:
        value = sanitise(env.get(name))
        if value:
            return value, name
    return None, None


def from_provider(ide: str | None) -> tuple[str | None, str | None]:
    """(model_id, source_name) from the active host's provider, or (None, None).

    NEVER RAISES. Opening a session must survive telemetry that does not work:
    a provider that throws, a providers package that is not importable, a host
    with no provider at all — each yields absence, and the session still opens.
    """
    if not ide:
        return None, None
    try:
        import providers

        provider = providers.get(ide)
    except Exception:  # noqa: BLE001 — a broken provider must not stop a session
        return None, None
    if provider is None:
        return None, None
    try:
        value = sanitise(provider.get_active_model())
    except Exception:  # noqa: BLE001 — same reason
        return None, None
    return (value, f"provider:{ide}") if value else (None, None)


def _detected_ide() -> str | None:
    """The host, asked of the one detector that answers it. Never guessed."""
    try:
        from skill_profile_detect import detect_ide

        return detect_ide()
    except Exception:  # noqa: BLE001
        return None


def resolve(
    environ: Mapping[str, str] | None = None, ide: str | None = AUTO
) -> dict[str, str | None]:
    """{'model_id', 'model_version', 'source'} — the chain, in declared order.

    ``source`` names WHICH step answered, so a wrong model id can be traced to
    the thing that supplied it instead of being argued about. When nothing
    answers, `model_id` is None and `source` is None: absence, not a guess.

    ``ide`` left at :data:`AUTO` detects the host; passing None asks NO provider
    at all. See the note on the sentinel.
    """
    env = os.environ if environ is None else environ
    model_id, source = from_env(env)
    if not model_id:
        model_id, source = from_provider(_detected_ide() if ide == AUTO else ide)
    return {
        "model_id": model_id,
        "model_version": sanitise(env.get("TAUSIK_AGENT_MODEL_VERSION")),
        "source": source,
    }
