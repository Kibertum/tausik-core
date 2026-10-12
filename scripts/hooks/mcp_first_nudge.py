"""Compatibility shim: the hook moved to `tool_choice_nudge.py`.

WHY THIS FILE EXISTS AND WHAT IT COSTS. A host reads `settings.json` when the
session starts. Renaming a deployed hook therefore breaks the RUNNING session —
bootstrap rewrites the settings, the file at the old path is gone, and every
subsequent tool call reports a hook that cannot be found. That happened during
the rename itself, which is how the case was found rather than reasoned about;
it will happen to anyone who upgrades mid-session.

So the old name delegates. It does not reimplement anything: a second copy of
the logic would drift from the first, and there is no reason for two.

REMOVAL: 1.10, once no session can plausibly still hold settings from before
this release. Deleting it earlier trades a real user-visible break for a tidier
directory listing.
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

if __name__ == "__main__":
    try:
        from tool_choice_nudge import main
    except Exception:  # noqa: BLE001 - a shim must never fail the call it follows
        sys.exit(0)
    main()
