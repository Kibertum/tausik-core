"""What the DEVELOPMENT lane last said about the branch being pushed.

`ci_lane_status` reads the PUBLISHED lane, on the default branch, and that is the
right thing for a release. It is the wrong thing for the branch the work is on:
MEASURED in session #277, that reader answered "published lane Tests is GREEN" ten
times in a row while naming a pipeline from thirteen days earlier, because the
published lane had not moved. Meanwhile nine of the last ten pipelines on the
working branch were RED -- every push of the session -- and no checkpoint said so.

WHAT THAT COST, precisely, because "unread redness" sounds abstract. Stages run in
order, so a red test stage never lets the full-battery stage start: the job that
carries `-m ''` was SKIPPED on every one of those pipelines. Two tests broken
deterministically therefore survived a whole release -- deselected by the local
default lane, and never reached by the only lane that would have run them. One
unread failure hid an entire class.

THE SAME THREE RULES `ci_lane_status` STATES, and they are not restated out of
politeness -- this module is the second reader on the same chokepoint and a
disagreement between them would be worse than either alone:

1. REPORT, DO NOT BLOCK. Whether to push over a red lane is the owner's call.
2. "NOT CHECKED" IS NEVER "OK". No client, no network, a timeout, a malformed
   answer -- each says so in words, naming the reason. A check that could not run
   must not read as a check that passed.
3. BEST EFFORT TO THE LAST. Nothing here may cost a push ticket that lives sixty
   seconds.

WHY THIS FILE IS NOT PUBLISHED. It is development-line tooling for a host the
public repository has no relationship with, and the owner's instruction is that it
stays behind. It is named in `publication_snapshot.EXCLUDED_FROM_PUBLIC_SNAPSHOT`,
and the caller imports it OPTIONALLY so the published tree works without it.

NO HOST NAME IS WRITTEN DOWN HERE, and that is a second line of defence rather
than a redundancy: the project's leak guard already refuses the internal host in
published files, so a literal would have to be remembered by whoever moves this
code. Derived from the remote, there is nothing to remember and nothing to redact.
"""

from __future__ import annotations

import json
import shutil
import subprocess

#: Seconds. Under the push ticket's own sixty, and under what a reader will wait.
DEFAULT_TIMEOUT = 8

#: The job whose colour answers "do the tests pass". Named rather than taking the
#: pipeline's own status: a pipeline is red when any job is, including ones whose
#: failure says nothing about the tests.
VERIFICATION_JOB = "tests"

#: The job that reaches slow-marked tests. Its SKIP is the finding that matters --
#: green-because-not-run is the exact confusion this whole module exists against.
FULL_BATTERY_JOB = "tests-full"

_CLIENT = "glab"


def _run(argv: list[str], timeout: int) -> tuple[int, str, str]:
    """Best effort. A missing client or a timeout is an answer, not an exception."""
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return 127, "", "client not installed"
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"
    except OSError as exc:
        return 126, "", str(exc)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def has_dev_remote(remotes: str) -> bool:
    """Whether a non-GitHub remote exists at all.

    Absence is the normal state for a consumer of the framework, and it must read
    as "nothing to check here", never as a fault.
    """
    for line in remotes.splitlines():
        parts = line.split()
        if len(parts) >= 2 and "github.com" not in parts[1]:
            return True
    return False


def _jobs(pipeline: dict) -> dict[str, str]:
    raw = pipeline.get("jobs")
    if not isinstance(raw, list):
        return {}
    out: dict[str, str] = {}
    for job in raw:
        if isinstance(job, dict) and isinstance(job.get("name"), str):
            out[job["name"]] = str(job.get("status", "unknown"))
    return out


def fetch_jobs(ident: object, timeout: int) -> dict[str, str]:
    """Job statuses for one pipeline, or `{}` when they cannot be read.

    A SECOND call, and it earns itself. The listing carries no `jobs` field at all
    -- measured against the live client -- so reading the job level from the listing
    would have been dead code that silently never warned about anything. This was
    caught before shipping by asking what the listing actually contains.

    Called only when the pipeline is NOT green, which is where the question matters:
    stages run in order, so a red earlier stage is exactly what leaves the
    full-battery job unrun, and a green pipeline has already run everything.
    """
    rc, out, _err = _run([_CLIENT, "ci", "get", "-p", str(ident), "--output", "json"], timeout)
    if rc != 0:
        return {}
    try:
        parsed = json.loads(out)
    except (ValueError, TypeError):
        return {}
    return _jobs(parsed) if isinstance(parsed, dict) else {}


def describe(branch: str, remotes: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str]:
    """`(state, message)` for the development lane on `branch`.

    `state` is `"pass"`, `"fail"`, `"running"`, `"skip"` or `"unknown"`. `"skip"`
    means there is no development remote, which is not a fault and not a pass.
    `"unknown"` is a real answer that names why the lane could not be read.
    """
    if not branch:
        return "unknown", "no branch name — the development lane was not checked"
    if not has_dev_remote(remotes):
        return "skip", ""
    if not shutil.which(_CLIENT):
        return "unknown", (
            f"development lane NOT CHECKED — `{_CLIENT}` is not installed. Not checked is not green."
        )
    rc, out, err = _run(
        [_CLIENT, "ci", "list", "--ref", branch, "--per-page", "1", "--output", "json"],
        timeout,
    )
    if rc != 0:
        reason = (err or out or "no output").strip().splitlines()[-1][:120]
        return "unknown", f"development lane NOT CHECKED — {reason}. Not checked is not green."
    try:
        parsed = json.loads(out)
    except (ValueError, TypeError):
        return "unknown", (
            "development lane NOT CHECKED — the client's answer did not parse as JSON. "
            "Not checked is not green."
        )
    runs = parsed if isinstance(parsed, list) else parsed.get("pipelines")
    if not isinstance(runs, list) or not runs:
        return "unknown", f"no pipeline recorded for `{branch}` — nothing to read, not a pass"
    newest = runs[0] if isinstance(runs[0], dict) else {}
    status = str(newest.get("status", "unknown")).lower()
    ident = newest.get("id") or newest.get("iid") or "?"
    # Job level only when the colour is not green: that is where "which job" and
    # "what never ran" are the question, and it keeps the common path at one call.
    jobs = {} if status == "success" else fetch_jobs(ident, timeout)
    full = jobs.get(FULL_BATTERY_JOB)
    tail = ""
    if full in {"skipped", "manual", "created"}:
        tail = (
            f"; `{FULL_BATTERY_JOB}` is {full} — the slow-marked tests were NOT run, "
            "so this colour says nothing about them"
        )
    if status in {"running", "pending", "created", "waiting_for_resource", "preparing"}:
        return "running", f"development lane on `{branch}` is {status} (#{ident}){tail}"
    if status == "success":
        return "pass", f"development lane on `{branch}` is GREEN (#{ident}){tail}"
    if status in {"failed", "canceled", "cancelled"}:
        which = jobs.get(VERIFICATION_JOB)
        named = f", job `{VERIFICATION_JOB}` {which}" if which else ""
        return "fail", f"development lane on `{branch}` is {status.upper()} (#{ident}){named}{tail}"
    return "unknown", f"development lane on `{branch}` reports `{status}` (#{ident}) — unread{tail}"


def report(branch: str, remotes: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str]:
    """`describe`, with every unexpected fault degraded to one honest line."""
    try:
        return describe(branch, remotes, timeout)
    except Exception as exc:  # noqa: BLE001 — reporting must never break the ticket
        return "unknown", f"development lane NOT CHECKED ({type(exc).__name__}) — read it yourself"
