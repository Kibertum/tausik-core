"""What the PUBLISHED verification lane last said — read at the moment it matters.

The write gate and the test suite are read constantly. The lane that verifies a
release is read when someone thinks to look, and on 2026-08-25 nobody did: three
`windows-latest` jobs went red, the run stayed red for nine days, and the
commits publishing the 1.9 work went out over it. A gate whose redness no one
reads is indistinguishable from a gate that is switched off — the thesis of the
whole `gates-declare-what-they-prevent` story, arriving this time as a fact
about attention rather than about code.

So the verdict is surfaced at the CHOKEPOINT OF PUBLISHING: `tausik push-ok`,
the one command that already stands before every push and already needs the
network. Nothing else in the toolchain has both properties — `doctor` is run
offline and in clean clones, and paying a network round trip there would make
the common case slower and the offline case ambiguous.

THREE RULES, and the second is the one this project keeps having to relearn.

1. REPORT, DO NOT BLOCK. Whether to publish over a red lane is the owner's
   call; this module's job is to make sure the call is INFORMED, not to make it.
   A gate that refuses here would be argued with, then switched off.

2. "NOT CHECKED" IS NEVER "OK". No `gh`, no network, not a GitHub remote, a
   timeout, a malformed answer — each says so, in words, naming the reason.
   Reporting silence as health is the exact defect this release is full of:
   a check that could not run must not read as a check that passed.

3. A HARD DEADLINE. `push-ok` writes a ticket that lives sixty seconds. A status
   read that hangs would spend the ticket's life, so the deadline is short and
   the failure is a plain "not checked".
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

#: Seconds. Deliberately well under the push ticket's own lifetime.
DEFAULT_TIMEOUT = 8

#: The lane whose verdict is worth interrupting a push for. Named rather than
#: "the newest run of anything", because the repository also runs coverage and
#: review bots whose colour says nothing about whether the tests pass.
VERIFICATION_WORKFLOW = "Tests"


def _run(argv: list[str], timeout: int) -> tuple[int, str, str]:
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
        return 127, "", "not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timed out after %ds" % timeout
    except OSError as exc:  # pragma: no cover — platform-specific spawn failure
        return 1, "", str(exc)
    return proc.returncode, proc.stdout or "", (proc.stderr or "").strip()


def github_slug(remotes: str) -> str | None:
    """`owner/repo` for the first GitHub remote in `git remote -v` output."""
    for line in remotes.splitlines():
        parts = line.split()
        if len(parts) < 2 or "github.com" not in parts[1]:
            continue
        url = parts[1]
        tail = url.split("github.com", 1)[1].lstrip(":/")
        if tail.endswith(".git"):
            tail = tail[:-4]
        if tail.count("/") == 1 and all(tail.split("/")):
            return tail
    return None


def describe(slug: str | None, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str]:
    """`(state, message)` for the published verification lane.

    `state` is one of `"pass"`, `"fail"`, `"running"` or `"unknown"`. The last
    one is a real answer, not an absence: it means the lane could not be read,
    and the message says why. A caller must never render it as health.
    """
    if not slug:
        return "unknown", "no GitHub remote — the published lane was not checked"
    rc, out, err = _run(
        [
            "gh",
            "run",
            "list",
            "--repo",
            slug,
            "--workflow",
            VERIFICATION_WORKFLOW,
            "--limit",
            "1",
            "--json",
            "databaseId,conclusion,status,headBranch,createdAt",
        ],
        timeout,
    )
    if rc == 127:
        return "unknown", "gh CLI not installed — the published lane was not checked"
    if rc == 124:
        return "unknown", "gh timed out — the published lane was not checked"
    if rc != 0:
        detail = err.splitlines()[0] if err else "exit %d" % rc
        return "unknown", "gh failed (%s) — the published lane was not checked" % detail
    try:
        runs: Any = json.loads(out)
    except ValueError:
        return "unknown", "gh returned unreadable output — the published lane was not checked"
    if not isinstance(runs, list) or not runs:
        return "unknown", "no run of workflow %r found — nothing to report" % VERIFICATION_WORKFLOW

    run = runs[0]
    conclusion = run.get("conclusion") or ""
    status = run.get("status") or ""
    where = "%s #%s, %s" % (
        run.get("headBranch") or "?",
        run.get("databaseId") or "?",
        (run.get("createdAt") or "?")[:10],
    )
    if status and status != "completed":
        return "running", "published lane %s is still %s (%s)" % (
            VERIFICATION_WORKFLOW,
            status,
            where,
        )
    if conclusion == "success":
        return "pass", "published lane %s is GREEN (%s)" % (VERIFICATION_WORKFLOW, where)
    if conclusion:
        return "fail", "published lane %s is %s (%s)" % (
            VERIFICATION_WORKFLOW,
            conclusion.upper(),
            where,
        )
    return "unknown", "run %s reports no conclusion — the lane's verdict is unreadable" % where


def report(remotes: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str]:
    """`describe` for whichever GitHub remote `git remote -v` shows."""
    return describe(github_slug(remotes), timeout)
