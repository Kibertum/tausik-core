#!/usr/bin/env python3
"""Per-session ledger of file Reads, so an unchanged file is not paid for twice.

MEASURED BEFORE BUILT (session #229, all 42 transcripts of this project). Of 285
Read calls carrying a path, 111 repeated a path already read in the same
conversation; 43 of those followed an Edit/Write and were legitimate. 68 remain —
23.9% of reads — and they are what this exists to stop.

THE PRIZE IS SMALL AND IS NAMED RATHER THAN IMPLIED. The release's own instrument
attributes 370,213 tokens of context growth to Read out of 17,896,506 — 2.07%. So
eliminating EVERY read would save 2.07%, and this mechanism's target is about
0.49%. The bulk of re-reading in this corpus does not go through the Read tool at
all: 2,196 genuine file reads happen inside Bash (`cat`, `sed -n`, `head <file>`)
with 604 avoidable repeats, roughly 3.1% of growth. Covering those would mean
BLOCKING a call after parsing arbitrary shell, and this project already has an
open, owner-held defect showing that shell parsing for gating misfires here
(`write-gate-reads-prose-arguments-as-redirections`). So this covers the Read
tool, and says plainly what it does not cover.

THE WINDOW IS A NUMBER, NOT A GUESS. A deny outside the window would be a silent
data cut: content read 400 calls ago may have left the context through
compaction, and refusing to re-read it would hand the agent an absence it cannot
detect. Measured gap between repeats — Read: median 4, p75 58, p90 187; Bash:
median 6, p75 37, p90 148. A window of 20 calls covers 69.4% of Read repeats and
65.6% of Bash ones, and everything beyond it is allowed through. That is the
trade this module makes explicit: two thirds of the saving, none of the risk of
denying something the model can no longer see.

OFF BY DEFAULT. Enabling is `read_ledger.enabled` in `.tausik/config.json`. A
mechanism that can refuse a read has to be chosen, not inherited.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any

# Own directory FIRST: `_common` below is a SIBLING imported by bare name, and
# scripts/hooks reaches sys.path only when this file is RUN as a script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Calls of distance beyond which a repeat is ALLOWED through. Measured, not
#: chosen: 20 covers 69.4% of this project's Read repeats and 65.6% of the Bash
#: ones, while leaving the long tail — where compaction may already have dropped
#: the content — untouched.
DEFAULT_WINDOW_CALLS = 20

#: Files above this size are compared by mtime+size alone. Hashing a 40 MB file
#: on every Read would spend more than the read it is trying to save.
MAX_HASH_BYTES = 2 * 1024 * 1024


def ledger_path(project_dir: str) -> str:
    return os.path.join(project_dir, ".tausik", "read_ledger.json")


def is_enabled(project_dir: str) -> bool:
    """Opt-in, and silent about it. Absent config means OFF."""
    try:
        from tausik_utils import load_effective_config

        cfg = load_effective_config(project_dir)
    except Exception:  # noqa: BLE001 — a hook may not die on an unreadable config
        return False
    section = cfg.get("read_ledger")
    if isinstance(section, dict):
        return bool(section.get("enabled"))
    return bool(cfg.get("read_ledger_enabled"))


def window_calls(project_dir: str) -> int:
    try:
        from tausik_utils import load_effective_config

        cfg = load_effective_config(project_dir)
        section = cfg.get("read_ledger")
        if isinstance(section, dict):
            v = section.get("window_calls")
            if isinstance(v, int) and v > 0:
                return v
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_WINDOW_CALLS


def fingerprint(path: str) -> dict[str, Any] | None:
    """(mtime, size, sha256-or-None) for a file, or None when it cannot be read.

    BOTH mtime AND a content hash, because each lies on its own. mtime changes on
    a checkout that restored identical bytes — trusting it alone would let a
    re-read through for nothing. A hash alone is expensive on large files and
    says nothing about a file replaced by identical content from a different
    source. Together they answer the only question that matters: is what is on
    disk now the same as what was read before.
    """
    try:
        st = os.stat(path)
    except OSError:
        return None
    digest: str | None = None
    if st.st_size <= MAX_HASH_BYTES:
        try:
            with open(path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
        except OSError:
            digest = None
    return {"mtime": st.st_mtime, "size": st.st_size, "sha256": digest}


def unchanged(before: dict[str, Any], now: dict[str, Any]) -> bool:
    """True only when the file is demonstrably the same as when it was read.

    A missing hash on EITHER side means "not demonstrated" — the answer is False,
    the read goes through. An unknown is never resolved in favour of refusing.
    """
    if before.get("size") != now.get("size"):
        return False
    if before.get("sha256") and now.get("sha256"):
        return before["sha256"] == now["sha256"]
    if before.get("sha256") or now.get("sha256"):
        return False  # one side unhashed: not demonstrated
    return before.get("mtime") == now.get("mtime")


def load_ledger(project_dir: str, session_id: Any) -> dict[str, Any]:
    """The ledger for THIS session. A different session starts empty.

    Session-scoped on purpose: the claim being made is "this content is already
    in the context", and a context does not survive a session.
    """
    try:
        with open(ledger_path(project_dir), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {"session_id": session_id, "calls": 0, "files": {}}
    if not isinstance(data, dict) or data.get("session_id") != session_id:
        return {"session_id": session_id, "calls": 0, "files": {}}
    data.setdefault("calls", 0)
    data.setdefault("files", {})
    return data


def save_ledger(project_dir: str, ledger: dict[str, Any]) -> bool:
    tausik = os.path.join(project_dir, ".tausik")
    if not os.path.isdir(tausik):
        return False
    tmp = ledger_path(project_dir) + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(ledger, fh, ensure_ascii=False)
        os.replace(tmp, ledger_path(project_dir))
        return True
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def decide(
    ledger: dict[str, Any], path: str, now: dict[str, Any] | None, window: int
) -> tuple[bool, str]:
    """(deny, reason). Deny only for a demonstrably unchanged file inside the window.

    Every uncertainty resolves to ALLOW: no fingerprint, no previous record, a
    changed file, or a distance beyond the window. The cost of a wrong allow is
    some tokens; the cost of a wrong deny is the agent reasoning about content it
    cannot see, which is the failure this framework calls intolerable.
    """
    if now is None:
        return False, "file not readable for fingerprinting"
    record = (ledger.get("files") or {}).get(path)
    if not isinstance(record, dict):
        return False, "first read of this file in this session"
    distance = int(ledger.get("calls", 0)) - int(record.get("call_no", 0))
    if distance > window:
        return False, f"last read {distance} calls ago, beyond the {window}-call window"
    if not unchanged(record, now):
        return False, "file changed since the last read"
    return True, (
        f"unchanged since call #{record.get('call_no')} of this session "
        f"({distance} calls ago, window {window})"
    )
