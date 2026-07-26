"""Single guarded git subprocess primitive (git-exec-single-wrapper).

Every git call in the framework funnels through here so `stdin=subprocess.DEVNULL`
is impossible to forget. The reason is a real, recurring defect:

  Inside the MCP server, `sys.stdin` is the JSON-RPC pipe to the IDE. On Windows
  git probes stdin (paginator / credential prompt) and blocks reading it, hanging
  the worker — defect `v14b-defect-mcp-task-done-stdin-hang`. The guard was lost
  once by copy-paste (risk_compute.py, then restored) and one gate-reachable site
  (`hooks/git_push_gate._git_head_sha`) shipped without it purely by luck (its
  stdin happened to be consumed earlier). Centralising the guard here makes that
  regression class unrepeatable: a git call that forgets DEVNULL cannot exist if
  the only way to spawn git is through `run_git`.

Two entry points, one guarantee:

  * ``run_git(cmd, **kwargs)`` — the core. `subprocess.run`-compatible so it is a
    drop-in default for modules with an injectable test-runner seam (e.g.
    ``verify_git_diff``). Forces ``stdin=DEVNULL`` via ``setdefault`` (an explicit
    stdin the caller passes still wins — the guard only fills the gap).
  * ``run(args, *, timeout, ...)`` — ergonomic sugar built on ``run_git``: no
    ``"git"`` prefix, ``capture_output=True``, text/binary switch. ``timeout`` is a
    REQUIRED keyword — there is no framework-wide default because the right bound
    is call-specific, and an unbounded git call is itself a hang risk.

Neither raises on a non-zero exit unless ``check=True`` — callers inspect
``returncode`` (matching the historical ``check_output`` sites that caught
``CalledProcessError`` and returned ``None``).
"""

from __future__ import annotations

import subprocess
from typing import Any


def run_git(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Run a git command with stdin ALWAYS closed (DEVNULL).

    `subprocess.run`-compatible: `cmd` is the full argv (``["git", ...]``) and
    kwargs pass straight through. `stdin` defaults to `DEVNULL` and can only be
    overridden by a caller that explicitly passes its own `stdin` (none do — the
    parameter exists so the guard is a floor, not a ceiling). Use this directly
    only where a `subprocess.run` signature is required (injectable-runner seams);
    prefer `run` everywhere else.

    ``stdin`` is passed as an explicit keyword (not folded into ``**kwargs``) so
    the AST anti-regression scan in test_risk_compute_stdin sees the guard here —
    this module is the ONE sanctioned ``subprocess.run`` of a git command.
    """
    stdin = kwargs.pop("stdin", subprocess.DEVNULL)
    return subprocess.run(cmd, stdin=stdin, **kwargs)


def run(
    args: list[str],
    *,
    cwd: str | None = None,
    timeout: float,
    text: bool = True,
    binary: bool = False,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """Run ``git <args>`` (no leading "git"), capturing stdout/stderr.

    - ``timeout`` is REQUIRED (keyword-only): every caller states its own bound.
    - ``binary=True`` returns bytes stdout/stderr; otherwise text is decoded.
    - ``check`` is False by default: a non-zero exit yields a CompletedProcess
      with ``returncode != 0`` for the caller to handle, never an exception.

    stdin is closed by ``run_git`` — a captured git call can never block on the
    inherited (MCP) stdin pipe.

    In text mode stdout/stderr are decoded utf-8 with ``errors="replace"`` — the
    defensive decoding every historical call site used, so odd bytes in a branch
    name or path never crash the decode.
    """
    as_text = text and not binary
    text_kwargs = {"encoding": "utf-8", "errors": "replace"} if as_text else {}
    return run_git(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=as_text,
        timeout=timeout,
        check=check,
        **text_kwargs,
    )
