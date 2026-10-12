"""Which project does this request belong to? One chain, three links, no ambient state.

THE ORDER CHANGED ONCE ALREADY, and the reason is why the first link is a PARAMETER. The
chain used to start at MCP roots. The spec of 2026-07-28 deprecates them (SEP-2577), so
building the foundation of project resolution on a deprecated primitive would have booked a
rewrite into the base. The spike that followed measured the replacement: the server config
mechanism (argv plus the working directory the host sets) is what works and is already in
production, with a tool parameter available should an HTTP transport ever unpin the process
from a window.

SO THE FIRST LINK IS SUPPLIED, NOT READ. `primary_signal` is whatever the host gave the
caller — an absolute path, or a `file://` URI, which is the shape roots arrive in. Should the
transitional path ever be needed, a roots value passes through the same parameter and this
module does not change. A module that decided for itself which mechanism to trust would have
to be rewritten every time the answer moved.

ISOLATED ON PURPOSE: no database, no network, no `os.getcwd()`, no `os.environ`. Everything it
reads arrives as an argument, which is what makes every branch of the priority order testable
without a fixture that has to pretend to be a machine. The one thing it does touch is the
filesystem, and only to answer "does this directory exist" — a resolver that returned a dead
path would be worse than one that returned nothing, because the caller would take it for a
working project.

THE ANSWER IS A PROJECT DIRECTORY OR None. Never a guess, never a path that is not there.
"""

from __future__ import annotations

import json
import os
from typing import Callable, Final, Mapping, NamedTuple
from urllib.parse import unquote, urlparse

#: The pointer's place. It sits under the 1.10 user tier rather than in `~/.tausik`, because a
#: directory of that name in the home folder makes the home folder look like a project — the
#: mistake `default_user_config_path` already documents and moved away from.
POINTER_RELATIVE: Final[str] = os.path.join(".config", "tausik", "active-project.json")

#: Keys tried inside the pointer, most specific first. A session id addresses one conversation;
#: a pid addresses one process; `default` is the single-project machine that never set either.
#: Tried in order so a machine with all three does not depend on dictionary order for its answer.
POINTER_KEY_ORDER: Final[tuple[str, ...]] = ("session", "pid", "default")


class Resolution(NamedTuple):
    """The answer and WHICH link produced it. ``project_dir`` is None when none did."""

    project_dir: str | None
    source: str  # "primary" | "pointer" | "walk-up" | "none"
    notes: tuple[str, ...]  # skipped links, each with the reason it was skipped


def normalise_signal(signal: str | None) -> str | None:
    """A path from an absolute path or a ``file://`` URI, or None.

    THE URI FORM IS THE TRANSITIONAL PATH (AC-6): roots arrive as `file://` URIs, so accepting
    one here is what lets a roots value flow through `primary_signal` without this module
    changing. `file:///C:/x` and `file:///home/x` both appear, and Windows leaves a leading
    slash in front of the drive letter that has to come off.
    """
    if not signal or not signal.strip():
        return None
    raw = signal.strip()
    if raw.lower().startswith("file://"):
        parsed = urlparse(raw)
        path = unquote(parsed.path)
        if parsed.netloc and parsed.netloc.lower() not in ("", "localhost"):
            return None  # a UNC-style file URI names another machine, which is not our project
        if os.name == "nt" and len(path) > 2 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        raw = path
    if not raw:
        return None
    return os.path.abspath(os.path.expanduser(raw))


def _is_project(path: str | None) -> bool:
    """A directory that holds `.tausik/`. Existence of BOTH is the whole predicate."""
    return bool(path) and os.path.isdir(os.path.join(str(path), ".tausik"))


def pointer_path(env: Mapping[str, str]) -> str:
    """`$TAUSIK_ACTIVE_POINTER`, else the user-tier file. Expanded, never created."""
    override = env.get("TAUSIK_ACTIVE_POINTER")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return os.path.join(os.path.expanduser("~"), POINTER_RELATIVE)


def read_pointer(path: str, keys: Mapping[str, str | None]) -> tuple[str | None, str | None]:
    """``(project_dir, skip_reason)`` from the pointer file.

    THREE SEPARATE FAILURES, and the acceptance criteria are right to insist they are three:
    an empty file, invalid JSON, and valid JSON without the key are different things that a
    single "broken pointer" test would leave two of unproven. Each returns its own reason, and
    none of them raises — a pointer that cannot be read is a link that is skipped, not a crash
    in the middle of resolving a project.
    """
    if not os.path.isfile(path):
        return None, None  # absence is not a failure; there simply is no pointer
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        return None, f"pointer unreadable ({e.__class__.__name__})"
    if not text.strip():
        return None, "pointer file is empty"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"pointer is not valid JSON (line {e.lineno})"
    if not isinstance(data, dict):
        return None, f"pointer holds {type(data).__name__}, expected an object"
    for kind in POINTER_KEY_ORDER:
        wanted = keys.get(kind)
        if kind != "default" and not wanted:
            continue
        table = data.get(kind)
        if kind == "default":
            value = data.get("default")
        elif isinstance(table, dict):
            value = table.get(str(wanted))
        else:
            value = None
        if isinstance(value, str) and value.strip():
            return normalise_signal(value), None
    return None, "pointer has no entry for this session, pid or default"


def resolve_project(
    primary_signal: str | None,
    env: Mapping[str, str],
    cwd: str,
    keys: Mapping[str, str | None] | None = None,
    log: Callable[[str], None] | None = None,
) -> Resolution:
    """Walk the chain and say which link answered.

    Order: the host's own signal, then the machine's active pointer, then a walk up from
    ``cwd``. Each link is checked for being a REAL project directory before it is accepted, so
    a stale pointer or a mistyped path drops through to the next link instead of being handed
    back. The notes say what was skipped and why: a resolver that silently fell through would
    make "no project here" and "your pointer is broken" the same answer.
    """
    notes: list[str] = []

    def note(msg: str) -> None:
        notes.append(msg)
        if log is not None:
            log(msg)

    candidate = normalise_signal(primary_signal)
    if primary_signal and candidate is None:
        note(f"primary signal {primary_signal!r} is not a usable path")
    elif candidate is not None:
        if _is_project(candidate):
            return Resolution(candidate, "primary", tuple(notes))
        note(f"primary signal {candidate!r} is not a TAUSIK project directory")

    path = pointer_path(env)
    pointed, reason = read_pointer(path, keys or {})
    if reason:
        note(f"{path}: {reason}")
    elif pointed is not None:
        if _is_project(pointed):
            return Resolution(pointed, "pointer", tuple(notes))
        # A DEAD POINTER IS WORSE THAN NONE: the caller would take the path for a working
        # project and fail somewhere the pointer is not mentioned.
        note(f"pointer names {pointed!r}, which is not a TAUSIK project directory")

    from project_config import tausik_dir_from

    found = tausik_dir_from(cwd, env)
    if os.path.isdir(found):
        return Resolution(os.path.dirname(os.path.abspath(found)), "walk-up", tuple(notes))
    note(f"no .tausik found walking up from {cwd!r}")
    return Resolution(None, "none", tuple(notes))
