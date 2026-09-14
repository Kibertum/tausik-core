"""The third link of the bootstrap chain: a RUNNING process versus the profile
it was started from.

`bootstrap_drift` compares two things on disk — `scripts/` source against the
deployed profile (`.claude/scripts/`, …) — and that closes two links of the
chain "edit → deploy → takes effect". Session #191 measured the third one:
after `bootstrap --ide all`, a fresh `gates status` listed the new gate, and
the MCP server that had been started BEFORE the redeploy closed two tasks in a
row without it. The server holds the registry and the handlers it imported at
start; redeploying the files under it changes nothing it will execute. Both
sides told the truth about different code, and nothing said so.

This module says so. At process start it takes a content snapshot of the tree
the process runs from; at task-done the gate asks whether that tree has
changed since. A change means the process is executing an older copy than the
one on disk — the gate set it is about to run, the handlers it is running, or
both — and closing a task on that evidence is refused with the one action that
fixes it: restart the process. A fresh CLI process is by construction never
stale; only a long-lived server can be.

CONTENT, NOT MTIME. A redeploy that rewrites identical files touches every
mtime and changes nothing that runs; a gate keyed on mtime would block after
every routine bootstrap and be switched off within a session. Files are
compared by hash, so only an actual change to something this process could
have loaded counts.

ONE SNAPSHOT PER PROCESS. `record_start` keeps the FIRST snapshot; a later
call does not move the point of reference, because a reference that any caller
can move is not a reference — the gate could be "cleared" by calling it again.

Reports, never restarts (decision #189): a live server cannot be told apart
from a stale one by the process tree, so the framework kills nothing.
"""

from __future__ import annotations

import hashlib
import os

#: What is snapshotted. Python only: it is what the interpreter loads. A
#: profile also carries JSON, Markdown and shell files, and a change to them
#: is real but is not "code this process already imported" — declared here
#: rather than half-covered.
_SUFFIXES = (".py",)
_SKIP_DIRS = frozenset({"__pycache__", ".git"})


def snapshot(root: str) -> dict[str, str]:
    """`relative path → sha1` for every Python file under `root`, recursively."""
    out: dict[str, str] = {}
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in filenames:
            if not name.endswith(_SUFFIXES):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, "rb") as fh:
                    digest = hashlib.sha1(fh.read()).hexdigest()  # noqa: S324 — identity, not security
            except OSError:
                continue  # vanished between listing and reading: reported by the next take
            out[os.path.relpath(path, root).replace(os.sep, "/")] = digest
    return out


class Snapshot:
    """The trees a process started from, and what has changed under them since."""

    def __init__(self, roots: list[str]) -> None:
        self.roots = [os.path.abspath(r) for r in roots]
        self.taken = {root: snapshot(root) for root in self.roots}

    def changed(self) -> list[str]:
        """Files whose content differs from the snapshot, plus files added or
        removed since — as `<root basename>/<relative path>`, sorted."""
        out: list[str] = []
        for root, then in self.taken.items():
            now = snapshot(root)
            label = os.path.basename(root)
            for rel in sorted(set(then) | set(now)):
                if then.get(rel) != now.get(rel):
                    out.append(f"{label}/{rel}")
        return out


_START: Snapshot | None = None


def record_start(*extra_roots: str) -> Snapshot:
    """Take the process-start snapshot of the tree THIS module runs from, plus
    any `extra_roots` (the MCP server passes its own `mcp/` directory, which
    lives outside the scripts tree).

    A root already snapshotted is never re-taken — the first snapshot is the
    reference, see the module docstring. A root seen for the first time is
    added with a snapshot taken now: the import-time call below knows only its
    own tree, and the server's explicit call at the top of `main` is the first
    moment its `mcp/` tree can be named, which is still its start.
    """
    global _START
    if _START is None:
        _START = Snapshot([os.path.dirname(os.path.abspath(__file__))])
    for root in extra_roots:
        root = os.path.abspath(root)
        if os.path.isdir(root) and root not in _START.taken:
            _START.roots.append(root)
            _START.taken[root] = snapshot(root)
    return _START


def changed_since_start() -> list[str]:
    """What has changed under the process's trees since `record_start`.

    A process that never recorded a start gets one now and reports nothing:
    the reference point is then "this instant", which is exactly right for a
    fresh CLI process and is the declared blind spot for a server that failed
    to call `record_start` at startup — the wiring test on the server's source
    is what keeps that blind spot from being the MCP server's actual state.
    """
    return record_start().changed()


# The import itself is the earliest moment this process can be observed, so
# the snapshot is taken here as well as in the server's explicit call: the
# explicit call pins the moment for the server, this pins it for anything
# that imports the gate before the server thought to.
record_start()
