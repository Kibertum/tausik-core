"""The text of the session commands, rendered ONCE for both surfaces.

`session current` is one line, and it was written twice. The two copies agreed
when this was collapsed — which is the point: agreement between two
implementations is a coincidence that has to be re-established after every
change, and nothing here was checking it. Sameness today is not sameness
tomorrow; one implementation is.
"""

from __future__ import annotations

from typing import Any


def session_current_line(svc: Any) -> str:
    """The open session, or the fact that there is none."""
    session = svc.session_current()
    if not session:
        return "No active session."
    return f"Session #{session['id']} started {session['started_at']}"
