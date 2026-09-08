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
import shlex

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
# Each wrapper maps to the options that take a SEPARATE value — the token after
# the flag belongs to the wrapper, not to the command being wrapped.
#
# Skipping the flag but not its value is how the wrapper went on hiding the
# command after the prefixes were being stripped: `sudo -u bob python h.py`
# stripped `sudo` and `-u`, then stopped at `bob`, called that the command, and
# never saw the interpreter. Measured over 19 wrapper forms: 8 blind, and
# `nice -n 5 python` was passing only because `5` happened to look like
# `timeout`'s duration. Every blind cell was a flag with a value.
#
# ONE table, keyed by the same names, at the same producer. A second list of
# wrapper names anywhere else would be the enumeration this layer exists to
# avoid — `_TRANSPARENT_PREFIXES` is derived from these keys rather than
# restated, so a wrapper cannot be added without its flags being considered.
# The long `--opt=value` spelling needs no entry: it is a single token.
_WRAPPER_VALUE_FLAGS: dict[str, frozenset[str]] = {
    "env": frozenset({"-u", "--unset", "-C", "--chdir"}),
    "sudo": frozenset(
        {
            "-u",
            "--user",
            "-g",
            "--group",
            "-p",
            "--prompt",
            "-C",
            "--close-from",
            "-D",
            "--chdir",
            "-h",
            "--host",
            "-r",
            "--role",
            "-t",
            "--type",
            "-U",
            "--other-user",
            "-R",
            "--chroot",
        }
    ),
    "doas": frozenset({"-u", "-C"}),
    "timeout": frozenset({"-s", "--signal", "-k", "--kill-after"}),
    "nice": frozenset({"-n", "--adjustment"}),
    "ionice": frozenset({"-c", "--class", "-n", "--classdata", "-p", "--pid", "-u", "--uid"}),
    "stdbuf": frozenset({"-i", "--input", "-o", "--output", "-e", "--error"}),
    "nohup": frozenset(),
    "command": frozenset(),
    "exec": frozenset(),
    # `xargs` RUNS the command that follows it, and measurement (session #238)
    # showed the parser blind to every one of them: `sh -c "echo x > f"` was
    # caught, `xargs -I{} sh -c "echo x > f"` was not — six forms, all at
    # `parsed` confidence, so the gate was not guessing, it saw no command.
    # Direction: a HOLE, not a false block.
    #
    # DECLARED RESIDUAL: what xargs actually writes can depend on STDIN, which
    # this parser cannot see. `xargs -I{} sh -c "echo x > {}"` writes wherever
    # the stream says, and `{}` is not a path — it is not offered as one. What
    # IS recovered is the command itself, parsed by the ordinary rules, so the
    # literal half (`xargs tee out.txt`, `xargs -I{} cp a b`) stops being
    # invisible. Claiming the other half would be a statement wider than the
    # evidence.
    #
    # ONLY THE FLAGS WHOSE VALUE IS MANDATORY when spelled detached. GNU xargs
    # gives `-e`, `-i` and `-l` OPTIONAL arguments, which in practice are glued
    # (`-i{}`); listing them here would make `xargs -i cp {} dst` eat `cp` as a
    # flag value and walk past the real command — going blind, which is the one
    # direction this table must never move (memory #524).
    "xargs": frozenset(
        {
            "-a",
            "--arg-file",
            "-d",
            "--delimiter",
            "-E",
            "--eof",
            "-I",
            "--replace",
            "-L",
            "--max-lines",
            "-n",
            "--max-args",
            "-P",
            "--max-procs",
            "-s",
            "--max-chars",
            "--process-slot-var",
        }
    ),
}

#: Flags whose value is not DATA but a COMMAND LINE. `env -S "tee out"` splits
#: its value into words, runs the first as the program, and appends every later
#: argv token as its arguments — so the value cannot be skipped over, it has to
#: be parsed.
#:
#: Kept apart from `_WRAPPER_VALUE_FLAGS` because putting `-S` in there was a
#: REGRESSION, found by review #7 in the same session that wrote it: consuming
#: the value as opaque dropped the real command from the stream, and
#: `env -S tee secret.txt` went from blocked (exit 2) to allowed (exit 0) while
#: a real GNU `env` writes the file. That is a blocking gate made WEAKER by a
#: commit whose purpose was making it stronger — memory #524, twice now.
#:
#: The distinction is the fix, not the exclusion: a flag either carries data,
#: and is skipped, or carries a command, and is descended into. Anything that
#: names a program belongs here.
_WRAPPER_COMMAND_FLAGS: dict[str, frozenset[str]] = {
    "env": frozenset({"-S", "--split-string"}),
}

_TRANSPARENT_PREFIXES = frozenset(_WRAPPER_VALUE_FLAGS)

# `FOO=1` / `PATH_X=/a/b` — an environment assignment `env` accepts before the
# command. Anchored at the token start so a filename containing '=' is not one.
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _carried_command(
    tok: str, sub: list[str], i: int, command_flags: frozenset[str]
) -> list[str] | None:
    """The command line a `-S`-style flag carries, plus the argv after it.

    `env -S "tee out"` and `env --split-string="tee out"` both mean: split the
    value into words, run the first as the program, and append everything that
    follows on the real command line. Returns None when `tok` is not such a
    flag, so the caller's ordinary flag handling continues.

    An unsplittable value (unbalanced quoting) yields None rather than raising:
    the caller then treats the flag as it always did, which leaves the gate no
    weaker than before rather than crashing a hook that runs on every command.
    """
    if not command_flags:
        return None
    value: str | None = None
    rest_at = i + 1
    if tok in command_flags and i + 1 < len(sub):
        value = sub[i + 1]
        rest_at = i + 2
    else:
        name, sep, attached = tok.partition("=")
        if sep and name in command_flags:
            value = attached
        else:
            # The GLUED short form, `-Stee out.txt`. Ordinary getopt syntax,
            # which real GNU env honours — verified: `env -S'tee f'` creates the
            # file. The first repair recognised only the spaced and `=` forms,
            # so this walked straight through in ONE step with no nesting at
            # all: a complete bypass of the class the repair announced closed.
            # Written as a rule over the short flags in the table, not a case
            # for `-S`, so a second command-carrying flag arrives covered.
            for flag in command_flags:
                if (
                    len(flag) == 2
                    and flag[0] == "-"
                    and flag[1] != "-"
                    and tok.startswith(flag)
                    and len(tok) > len(flag)
                ):
                    value = tok[len(flag) :]
                    break
    if value is None:
        return None
    try:
        words = shlex.split(value)
    except ValueError:
        return None
    if not words:
        return None
    return words + sub[rest_at:]


def _strip_prefixes(sub: list[str]) -> list[str]:
    """`sub` with leading run-another-command wrappers removed.

    Drops the prefix, its flags, THE VALUES ITS FLAGS TAKE, its `VAR=value`
    assignments (`env FOO=1 bash`), and — for `timeout` / `nice` / `ionice` —
    the one bare numeric argument they take before the real command. A bare
    non-numeric token ends the scan: that is the command being wrapped.

    The flag VALUE is the part that was missing, and it is the whole defect:
    `sudo -u bob python h.py` dropped `sudo` and `-u`, then read `bob` as the
    command and never reached the interpreter. Eight of nineteen measured
    wrapper forms were blind that way, and every one of them was a flag with a
    value. Which options take one is `_WRAPPER_VALUE_FLAGS`' answer, per
    wrapper, because there is no way to tell from the token alone.

    A flag NOT in that set consumes only itself. That direction matters as much
    as the other: eating an argument the wrapper does not take would swallow the
    command and blind the gate where it currently sees, so `env -i python h.py`
    is asserted alongside the forms this fixes.

    And a flag whose value IS a command line (`_WRAPPER_COMMAND_FLAGS`) is
    neither skipped nor eaten — it is split and re-entered. Skipping it was a
    regression: `env -S "tee out"` really runs `tee`, and consuming its value as
    opaque dropped the writer from the stream, turning a block into an allow.

    Returns `sub` unchanged when nothing was stripped, so the common case costs
    one set lookup.
    """
    return _strip(sub, _size(sub) + 1)


def _size(sub: list[str]) -> int:
    return sum(len(t) for t in sub)


def _strip(sub: list[str], budget: int) -> list[str]:
    """`_strip_prefixes`, with `-S`-style unwrapping bounded STRUCTURALLY.

    `env -S "env -S …"` is legal and nests. A counted depth limit was the first
    answer and it was the wrong one: on overflow it returned the still-wrapped
    tokens, whose head is `env` — not a writer, not a shell — so every consumer
    saw NOTHING. Measured: four levels of nesting were caught, five were
    silently allowed. A limit that turns a block into an allow one level past
    an arbitrary number is not a safety bound, it is the bug it was guarding
    against, wearing a constant.

    The bound is now the one fact that makes termination certain: each unwrap
    removes at least the wrapper word and its flag, so the token stream STRICTLY
    SHRINKS. Recursion continues only while it does. That resolves a chain of
    any realistic depth and still cannot loop, because a step which fails to
    shrink is refused — and refusing to loop is not the same as going blind: by
    then the stream has already been unwrapped as far as it shrank.
    """
    size = _size(sub)
    if size >= budget:
        return sub
    i = 0
    stripped = False
    while i < len(sub):
        base = os.path.basename(sub[i]).lower().removesuffix(".exe")
        if base not in _TRANSPARENT_PREFIXES:
            break
        takes_number = base in ("timeout", "nice", "ionice")
        value_flags = _WRAPPER_VALUE_FLAGS[base]
        command_flags = _WRAPPER_COMMAND_FLAGS.get(base, frozenset())
        i += 1
        stripped = True
        while i < len(sub):
            tok = sub[i]
            if tok.startswith("-") or _ASSIGNMENT_RE.match(tok):
                # A flag carrying a COMMAND LINE: split it and keep looking for
                # the real program inside, with the wrapper's remaining argv
                # appended exactly as `env -S` appends it.
                carried = _carried_command(tok, sub, i, command_flags)
                if carried is not None:
                    return _strip(carried, size)
                i += 1
                # `--opt=value` carries its value in the same token; `-o0` is an
                # attached short value. Only the detached spelling eats another.
                if tok in value_flags and i < len(sub):
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
