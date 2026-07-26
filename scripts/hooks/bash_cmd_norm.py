"""What command is a sub-command REALLY running — the layer under write detection.

Split out of `bash_write_parse` for the 400-line cap the framework enforces on
everyone else, along a seam that had already appeared twice in one session.
"What does this command write" and "what command is this, actually" are separate
questions, and both times the write detectors were correct while the answer to
the second was wrong:

* `bash -c 'echo x > f'` — the redirection sat inside one quoted token, so no
  detector could see it. Rule 1 and the scope ACL were bypassable by a one-liner
  of the class Decision #162 closed for heredocs.
* `env bash -c '…'` — the shell test then read `sub[0]`, which is `env`, so the
  same bypass survived one level further out. Found by adversarially reviewing
  the FIX for the first one (convention #276), not the code it replaced.

Both are answered here, before any detector runs. Anything that reads "is this a
`tee`?" or "is this a shell?" must normalise through `strip_prefixes` first,
or it is asking about the wrapper instead of the command.

Deliberately NOT applied to the redirection scan: a `>` is a `>` wherever it
stands, and narrowing that input could only lose targets.
"""

from __future__ import annotations

import os
import re

# Shells whose `-c` argument is a whole command line, not a filename. The
# redirection inside it lives in ONE quoted token, so every detector above sees
# a single opaque string: `bash -c 'echo x > scripts/foo.py'` used to yield no
# target at all, which made Rule 1 and the scope ACL bypassable by a one-liner
# of the same class Decision #162 closed for heredocs. The residual was
# documented as "must actively obfuscate"; `bash -c` is an everyday form.
_SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh", "ash", "busybox"})

# A wrapper may nest (`bash -c "sh -c '…'"`). Bounded so a crafted or accidental
# chain cannot spin: three levels is far past any real invocation, and the limit
# is a named constant rather than an implicit recursion depth so exceeding it is
# a decision, not a crash.
_MAX_WRAPPER_DEPTH = 3


# Commands that RUN another command rather than being one. `env bash -c 'echo x
# > f'` hid the wrapper exactly the way the wrapper hid the redirection — the
# same one-line bypass, one level further out — because the shell test looked at
# `sub[0]`, which is `env`. Found by adversarially reviewing the wrapper fix
# itself (convention #276), not the code it replaced.
#
# Closing this also reaches `sudo tee f`, which the residual boundary named as
# an uncaught "writer behind a wrapper". That is the intended consequence: the
# writer was never hidden by `tee`, only by what stood in front of it.
_TRANSPARENT_PREFIXES = frozenset(
    {"env", "sudo", "doas", "nohup", "nice", "ionice", "stdbuf", "timeout", "command", "exec"}
)

# `FOO=1` / `PATH_X=/a/b` — an environment assignment `env` accepts before the
# command. Anchored at the token start so a filename containing '=' is not one.
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _strip_prefixes(sub: list[str]) -> list[str]:
    """`sub` with leading run-another-command wrappers removed.

    Drops the prefix, its flags, its `VAR=value` assignments (`env FOO=1 bash`),
    and — for `timeout` / `nice` / `ionice` — the one bare numeric argument they
    take before the real command. A bare non-numeric token ends the scan: that
    is the command being wrapped.

    Returns `sub` unchanged when nothing was stripped, so the common case costs
    one set lookup.
    """
    i = 0
    stripped = False
    while i < len(sub):
        base = os.path.basename(sub[i]).lower().removesuffix(".exe")
        if base not in _TRANSPARENT_PREFIXES:
            break
        takes_number = base in ("timeout", "nice", "ionice")
        i += 1
        stripped = True
        while i < len(sub):
            tok = sub[i]
            if tok.startswith("-") or _ASSIGNMENT_RE.match(tok):
                i += 1
                continue
            if takes_number and _is_duration(tok):
                i += 1
                takes_number = False
                continue
            break
    if not stripped:
        return sub
    return sub[i:]


def _is_duration(tok: str) -> bool:
    """`5`, `1.5`, `30s`, `2m` — `timeout`'s argument, not a command."""
    body = tok[:-1] if tok[-1:] in "smhd" else tok
    try:
        float(body)
    except ValueError:
        return False
    return True


def _shell_payloads(sub: list[str]) -> list[str]:
    """Command strings carried as the `-c` argument of a POSIX shell in `sub`.

    `-c` is matched inside combined short flags too (`-lc`, `-ec`), because that
    is how the form is actually written. A long `--` option is not a short-flag
    cluster and is skipped, so `--color` does not read as containing `c`.

    Deliberately POSIX-shells-only: this is the descent `bash_write_parse` uses,
    and that parser feeds the BLOCKING scope/write gate (exit 2, no approval
    path). Widening it to other dialects would re-parse, say, a PowerShell
    payload as POSIX and risk a false BLOCK there. The DANGER scanner, whose
    posture is over-detect-then-WARN, asks `_interpreter_payloads` instead.
    """
    sub = _strip_prefixes(sub)
    if not sub:
        return []
    base = os.path.basename(sub[0]).lower().removesuffix(".exe")
    if base not in _SHELLS:
        return []
    out: list[str] = []
    for i, tok in enumerate(sub[1:], start=1):
        if not tok.startswith("-") or tok.startswith("--") or "c" not in tok:
            continue
        if i + 1 < len(sub):
            out.append(sub[i + 1])
        break
    return out


# Non-POSIX-shell interpreters whose command-carrying argument the DANGER
# scanner descends into. `_shell_payloads` covers the 7 POSIX shells; the
# scanner's `_INTERPRETERS` raw-joins 34 names, and for the gap between the two
# a nested command hidden behind an INNER quote survived unscanned
# (`powershell -c "powershell -c 'git push --force'"` reached the firewall as
# rc=0). The PowerShell scanner's `payloads` already descends its whole
# interpreter set; this brings the POSIX side to the same parity rather than
# inventing a second rule (conventions #266/#289).
#
# `ssh` and `wsl` are intentionally NOT here: `ssh host '<cmd>'` runs on a
# remote host whose paths and git remotes this firewall cannot reason about,
# and `wsl` has no `-c` form (its payload is a positional Linux command). Both
# are residuals on the PowerShell side too, so leaving them out keeps the two
# channels in step. A language interpreter's `-c` (`python -c '<code>'`) is
# code, not a shell command line, and is likewise left as a named residual.
_DASH_C_INTERPRETERS = frozenset({"powershell", "pwsh"})
_SLASH_C_INTERPRETERS = frozenset({"cmd"})


def _interpreter_payloads(sub: list[str]) -> list[str]:
    """Command strings `sub` hands to another interpreter to run — the DANGER
    scanner's descent, a superset of `_shell_payloads`.

    Covers a POSIX shell's `-c` (via `_shell_payloads`), PowerShell's `-c` /
    `-Command`, and `cmd`'s `/c` / `/k`. The argument is the token that follows.
    Over-detection is the safe direction here: re-scanning a payload that turns
    out to be inert costs a WARN a `TAUSIK_SKIP_HOOKS` escape can clear, while
    missing it is the confirmed bypass this closes.
    """
    payloads = list(_shell_payloads(sub))
    stripped = _strip_prefixes(sub)
    if not stripped:
        return payloads
    base = os.path.basename(stripped[0]).lower().removesuffix(".exe")
    is_dash_c = base in _DASH_C_INTERPRETERS
    is_slash_c = base in _SLASH_C_INTERPRETERS
    if not (is_dash_c or is_slash_c):
        return payloads
    for i, tok in enumerate(stripped[1:], start=1):
        low = tok.lower()
        # PowerShell binds `-Command` by any non-empty prefix of the WORD
        # "command" (`-c`, `-co`, …, `-command`). Testing `startswith("-c")`
        # instead swept in real, unrelated `-C*` switches — `-ConfigurationName`,
        # `-CustomPipeName`, `-Credential` — and grabbed THEIR value as the
        # payload, so the true `-Command` argument later in the line was never
        # descended into (review s126, HIGH). `-EncodedCommand` starts with `-e`
        # and never matched anyway; base64 stays a stated residual. `cmd` takes
        # `/c` or `/k`.
        hit = (
            is_dash_c and low.startswith("-") and len(low) > 1 and "command".startswith(low[1:])
        ) or (is_slash_c and low in ("/c", "/k"))
        if hit:
            if i + 1 < len(stripped):
                payloads.append(stripped[i + 1])
            break
    return payloads
