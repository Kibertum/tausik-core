"""Does this host say which model is running it — and if not, does anyone know?

session-model-recorded-on-non-claude-hosts. Model pinning (RENAR Rule 10.13) is
the mechanism that lets cost, first-pass success rate and throughput be
re-calibrated when the model changes mid-project. Measured in session #231 it had
fired exactly zero times in the project's history: 0 of 231 sessions carried a
model id, 0 of 1560 tasks carried a pin.

Nothing said so. That is the part this check exists for: a silent NULL looks
identical to a feature nobody needed, and the difference only shows up much later
as an empty column in a report someone was relying on.

THREE STATES, AND ONLY ONE IS A WARNING:

  * DECLARED   — a source answered, and the check names WHICH one, so a wrong id
                 can be traced to the thing that supplied it.
  * NOT ASKED  — no session is open. There is nothing to report, and inventing a
                 complaint here would light the check up on every fresh clone.
  * SILENT     — a session is open and carries no model. Not an error on the
                 user's part: most hosts genuinely do not export it. The line
                 names `TAUSIK_AGENT_MODEL` so the reader is handed the way out
                 rather than a grievance.

The check NEVER infers the model from the host. Claude Code pointed at z.ai
through `ANTHROPIC_BASE_URL` is running GLM, and reporting "claude, probably"
there would be worse than reporting nothing.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from agent_model_source import DECLARE_WITH, resolve

_LABEL = "Session model"


def check_session_model(svc: Any) -> Iterator[tuple[str, str, str]]:
    """One row: which source named the model for the open session, or none."""
    try:
        session = svc.be.session_current()
    except Exception:  # noqa: BLE001 — a check bug must not crash doctor
        return
    if not session:
        return  # no open session: nothing was asked, so nothing is missing

    recorded = session.get("model_id")
    if recorded:
        yield (
            "ok",
            _LABEL,
            f"session #{session.get('id')} recorded model={recorded} — task start and "
            "done pin it, and a mid-task change raises model_mismatch",
        )
        return

    # The session opened without a model. Ask the chain again for the reader's
    # benefit: if a source WOULD answer now, the session simply predates the fix,
    # and saying so is more useful than repeating that the column is empty.
    available = resolve().get("model_id")
    if available:
        yield (
            "warn",
            _LABEL,
            f"session #{session.get('id')} carries no model, but one is available "
            f"now ({available}). The session opened before the model source was "
            "wired; close it and open a new one to pin correctly",
        )
        return
    yield (
        "warn",
        _LABEL,
        f"session #{session.get('id')} carries no model and no source reports one. "
        f"Model pinning, cost per model and per-model metrics stay empty until the "
        f"host declares it: set {DECLARE_WITH} to the id actually serving this "
        "session. It is NOT guessed from the host — Claude Code pointed at another "
        "endpoint is running that endpoint's model, not Claude's",
    )
