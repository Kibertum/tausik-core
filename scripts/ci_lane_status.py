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
import math
import re
import subprocess
import time
from typing import Any
from urllib.parse import urlparse

#: Seconds. Deliberately well under the push ticket's own lifetime.
DEFAULT_TIMEOUT = 8

#: The lane whose verdict is worth interrupting a push for. Named rather than
#: "the newest run of anything", because the repository also runs coverage and
#: review bots whose colour says nothing about whether the tests pass.
VERIFICATION_WORKFLOW = "Tests"
PUBLISH_WORKFLOW = ".github/workflows/tests.yml"
PUBLISH_BRANCH = "main"
PUBLISH_EVENT = "push"
PUBLISH_WAIT_TIMEOUT = 90 * 60
PUBLISH_POLL_INTERVAL = 15


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


def _github_url_slug(url: str) -> str | None:
    """Parse only URLs whose actual host is github.com."""
    if "://" in url:
        parsed = urlparse(url)
        if (parsed.hostname or "").lower() != "github.com":
            return None
        tail = parsed.path.lstrip("/")
    else:
        match = re.fullmatch(r"(?:[^@/:]+@)?github\.com:(.+)", url, re.IGNORECASE)
        if not match:
            return None
        tail = match.group(1)
    if tail.endswith(".git"):
        tail = tail[:-4]
    if tail.count("/") == 1 and all(tail.split("/")):
        return tail
    return None


def github_slug(remotes: str) -> str | None:
    """`owner/repo` for the first structurally valid GitHub remote URL."""
    for line in remotes.splitlines():
        parts = line.split()
        if len(parts) >= 2 and (slug := _github_url_slug(parts[1])):
            return slug
    return None


def named_github_slug(remotes: str, remote_name: str) -> str | None:
    """One GitHub slug from every push URL of the named release remote."""
    urls = []
    for line in remotes.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == remote_name and parts[-1] == "(push)":
            urls.append(parts[1])
    slugs = [_github_url_slug(url) for url in urls]
    if not slugs or any(slug is None for slug in slugs) or len(set(slugs)) != 1:
        return None
    return slugs[0]


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


def describe_exact(slug: str | None, sha: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str]:
    """Verdict for the required workflow on one exact candidate SHA."""
    if not slug:
        return "unknown", "no GitHub repository — exact-SHA CI was not checked"
    rc, out, err = _run(
        [
            "gh",
            "run",
            "list",
            "--repo",
            slug,
            "--workflow",
            PUBLISH_WORKFLOW,
            "--commit",
            sha,
            "--branch",
            PUBLISH_BRANCH,
            "--event",
            PUBLISH_EVENT,
            "--limit",
            "20",
            "--json",
            "databaseId,conclusion,status,event,headBranch,headSha,createdAt,url",
        ],
        timeout,
    )
    if rc == 127:
        return "unknown", "gh CLI not installed — exact-SHA CI was not checked"
    if rc == 124:
        return "unknown", "gh timed out — exact-SHA CI was not checked"
    if rc != 0:
        detail = err.splitlines()[0] if err else f"exit {rc}"
        return "unknown", f"gh failed ({detail}) — exact-SHA CI was not checked"
    try:
        runs: Any = json.loads(out)
    except ValueError:
        return "unknown", "gh returned unreadable output — exact-SHA CI was not checked"
    if not isinstance(runs, list):
        return "unknown", "gh returned a non-list result — exact-SHA CI was not checked"
    exact = [
        run
        for run in runs
        if isinstance(run, dict)
        and run.get("headSha") == sha
        and run.get("event") == PUBLISH_EVENT
        and run.get("headBranch") == PUBLISH_BRANCH
    ]
    if not exact:
        return "missing", f"no {PUBLISH_EVENT} run of {PUBLISH_WORKFLOW!r} for exact SHA {sha[:12]}"
    run = exact[0]
    status = str(run.get("status") or "")
    conclusion = str(run.get("conclusion") or "")
    where = f"SHA {sha[:12]}, run #{run.get('databaseId') or '?'}"
    if status != "completed":
        if status:
            return "running", f"candidate {where} is still {status}"
        return "unknown", f"candidate {where} has no status — exact-SHA CI is unreadable"
    if conclusion == "success":
        return "pass", f"candidate {where} is GREEN"
    if conclusion:
        return "fail", f"candidate {where} is {conclusion.upper()}"
    return "unknown", f"candidate {where} has no terminal conclusion — exact-SHA CI is unreadable"


def wait_for_exact(
    slug: str | None,
    sha: str,
    timeout: int = PUBLISH_WAIT_TIMEOUT,
    poll_interval: int = PUBLISH_POLL_INTERVAL,
) -> tuple[bool, str]:
    """Wait a bounded time for exact-SHA success; every other terminal state refuses."""
    deadline = time.monotonic() + max(0, timeout)
    while True:
        remaining = deadline - time.monotonic()
        probe_timeout = max(1, min(DEFAULT_TIMEOUT, math.ceil(max(0, remaining))))
        state, message = describe_exact(slug, sha, timeout=probe_timeout)
        if state == "pass":
            return True, message
        if state in {"fail", "unknown"}:
            return False, message
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False, f"timed out waiting for exact SHA {sha[:12]}: {message}"
        time.sleep(min(max(0, poll_interval), remaining))
