#!/usr/bin/env python3
"""Bash write-target parser for `bash_write_gate` (l26-hook-contract-review).

Pure, side-effect-free parsing: given a Bash command string, return the file
paths it appears to write. Split out of `bash_write_gate.py` for the filesize
gate — the enforcement/DB half lives there, the command-parsing half here.

`write_targets(command)` is the public entry point. Everything else is a
best-effort detector for one write vector (redirection, tee, dd, sed -i, cp/mv,
curl/wget/tar/unzip, a literal open() in an interpreter payload OR in the Python
script that payload runs). The documented residual boundary lives in
docs/ru/enforcement-coverage.md.
"""

from __future__ import annotations

import os
import re
import shlex
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

# Imported from the scanner module, not from the hook. The hook now imports
# `shell_channel`, which imports this file — reaching back into it would close
# that loop into an import cycle.
from bash_cmd_scan import (  # noqa: E402
    _mentions_interpreter,
    _split_subcommands,
    command_changes_directory,  # noqa: F401 — re-exported: gate and tests import it here
)

# Redirections — which ones write, and which tokens they consume — live in
# `shell_redirection`, with the measurements that put them there. What used to
# stand here was `^\d*>>?\|?$|^&>>?$`, matched against one shlex token: the
# `\d*` expected `2>` to arrive as a single token, which it never does, and the
# orphaned `2` was then read as one of the command's own arguments (for
# `cp`/`mv`/`install`, as the destination itself). Openers of a process
# substitution are not redirections and are handled where the word list is read.
from shell_redirection import split_redirections, strip_fd_prefixes  # noqa: E402

# Where a relative path may point once the command has moved the shell. Its own
# module because the answer is a rule about the command text, not about writes:
# the same question decides a script path here and would decide any other
# relative operand a future gate reads. See `shell_roots` for the three
# successive wrong answers that produced it.
from shell_roots import resolution_roots  # noqa: E402
from shell_statements import split_statement_breaks  # noqa: E402

_PROC_SUB = ("<(", ">(")

# Reading PYTHON for its literal writes -- inline in the command text and
# inside a script file the command names -- is its own module: that half
# reads Python, everything here reads a shell command line, and the
# filesize gate made the seam worth taking. Re-exported under the private
# names this module has always used, so callers keep their names.
from python_invocation import SCRIPT_SUFFIXES as _SCRIPT_SUFFIXES  # noqa: E402,F401
from python_invocation import is_python as _is_python  # noqa: E402
from python_source_writes import MAX_SCRIPT_BYTES as _MAX_SCRIPT_BYTES  # noqa: E402,F401
from python_source_writes import OPEN_RE as _OPEN_RE  # noqa: E402
from python_source_writes import writes_in_script_file as _script_file_writes  # noqa: E402


# Opening marker of a heredoc. Group 1 = the `-` of `<<-` (tab-stripping form)
# or empty for a plain `<<`; group 3 = the delimiter word.
_HEREDOC_RE = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")

# A token still carrying '$' or a backtick after posix tokenization is an
# unexpanded variable or command substitution — genuinely unresolvable, the
# documented residual (`echo > $SCRATCH/x`). We deliberately do NOT reject
# ()<>|&*? here: after shlex posix tokenization, a token that survived WITH one
# of those chars was QUOTED in the source (unquoted shell metacharacters split
# into separate punctuation tokens), i.e. it is a legitimate literal filename
# like 'Copy (1).txt' or 'Q&A.md' — the SAFEST tokens to trust. Rejecting them
# silently dropped real in-tree writes (a worse hole than the one being closed).
_METACHARS = set("$`\n")


def _plausible_path(tok: str) -> bool:
    return bool(tok) and not (_METACHARS & set(tok))


def _strip_heredocs(command: str) -> str:
    """Remove heredoc BODIES, keeping the header line that holds the redirect.

    Without this, the whole raw command — including the heredoc body — is
    tokenized as live shell, so a bare `>` or `->` in prose/code inside the body
    manufactures a phantom redirect target (`def f() -> int:` -> target `int:`),
    which then blocks an otherwise-compliant write. The header line (`cat > f
    <<EOF`) is preserved so the real target `f` is still detected; everything
    from the next line up to and including the terminator is dropped.
    """
    lines = command.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        # A header line may open MORE THAN ONE heredoc (`cmd <<A <<B`); bash
        # consumes their bodies in order. finditer (not search) handles each, or
        # the second body leaks back into the scanned shell text.
        for m in _HEREDOC_RE.finditer(line):
            dash, delim = m.group(1), m.group(3)
            # bash: a plain `<<DELIM` needs an EXACT terminator line; `<<-DELIM`
            # strips only leading TABS. Using .strip() for the plain form let an
            # indented pseudo-delimiter inside the body end the scan early and
            # re-expose the rest of the body as live shell (phantom targets).
            while i < len(lines):
                base = lines[i].rstrip("\r")
                if (base.lstrip("\t") == delim) if dash else (base == delim):
                    break
                i += 1
            i += 1  # skip the terminator line itself (or past EOF if unterminated)
    return "\n".join(out)


def _opt_value(args: list[str], short: str | None, long: str | None) -> str | None:
    """Value of `-x VALUE` / `--long VALUE` / `--long=VALUE`, or None.

    For flags that name a WRITE target as their argument (cp -t, curl -o,
    tar -C, unzip -d): the target is a flag value, not a trailing positional.
    """
    for i, a in enumerate(args):
        if short and a == short and i + 1 < len(args):
            return args[i + 1]
        if long:
            if a == long and i + 1 < len(args):
                return args[i + 1]
            if a.startswith(long + "="):
                return a[len(long) + 1 :]
    return None


def _positionals(tokens: list[str]) -> list[str]:
    """Non-flag arguments, honouring a `--` end-of-options separator.

    After `--`, a token starting with `-` is a positional (a filename), not a
    flag: `cp -- -a.txt b.txt` writes to `b.txt`.
    """
    out: list[str] = []
    end_opts = False
    for a in tokens:
        if not end_opts and a == "--":
            end_opts = True
            continue
        if not end_opts and a.startswith("-"):
            continue
        out.append(a)
    return out


def tokenize(command: str) -> list[str] | None:
    """POSIX tokens, or None when unparseable — this dialect's entry point.

    Public because `shell_channel` routes "tokenize this the way that tool
    speaks" through the same table it uses for write targets. A consumer that
    picks a tokenizer itself is choosing a dialect by hand, and that is how the
    push gate came to read a PowerShell here-string with the POSIX lexer and
    find a `git push` in the prose of a commit message.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return None


def _redir_targets_regex(command: str) -> list[str]:
    """Fallback when the command won't tokenize (unbalanced quotes, a heredoc
    body carrying a lone quote). Over-detects rather than under-detects: a
    missed write is a hole, an extra candidate at worst asks for a task a real
    write would need anyway. A quoted '>' can produce a false candidate here —
    accepted, because failing toward gating is the safe direction for a
    command we could not parse.
    """
    out: list[str] = []
    for m in re.finditer(r"(?<![0-9&<])>>?\s*([^\s;&|<>()]+)", command):
        tgt = m.group(1)
        if not tgt.startswith("&"):
            out.append(tgt)
    return out


def _sed_files(args: list[str]) -> list[str]:
    """File targets of a `sed` invocation — only when it edits in place (-i).

    The subtlety: the sed SCRIPT is a bare token too. Without -e/-f it is the
    first positional (`sed -i 's/a/b/' FILE`); with -e/-f it is the argument
    that FOLLOWS the flag (`sed -i -e 's/a/b/' FILE`) and must be skipped, or
    the script itself is mistaken for a file. Returns [] when not in-place.
    """
    files: list[str] = []
    in_place = False
    script_via_flag = False
    skip_next = False
    end_opts = False
    for a in args:
        if skip_next:
            skip_next = False
            continue
        if not end_opts:
            if a == "--":
                end_opts = True  # everything after is a filename, even if -prefixed
                continue
            if a in ("-e", "-f", "--expression", "--file"):
                script_via_flag = True
                skip_next = True  # its argument is the script/script-file, not a file
                continue
            if a.startswith(("--expression=", "--file=")):
                script_via_flag = True
                continue
            if a == "-i" or a.startswith("-i") or a.startswith("--in-place"):
                in_place = True
                continue
            if a.startswith("-"):
                if "i" in a:  # combined short flags, e.g. -ni
                    in_place = True
                continue
        if a == "":
            # BSD `sed -i '' 's/…/…/' file`: the empty token is the backup-suffix
            # argument of BSD's -i, not a file. Dropping it lets the drop-first
            # 'inline script' rule land on the real script, not a phantom.
            continue
        files.append(a)
    if not in_place:
        return []
    if not script_via_flag and files:
        files = files[1:]  # the first bare arg was the inline script
    return files


# The "what command is this really" layer lives in bash_cmd_norm (filesize cap).
# Re-exported so a future reader of this module still finds the names it uses.
from bash_cmd_norm import (  # noqa: E402,F401 — re-exported
    _MAX_WRAPPER_DEPTH,
    _shell_payloads,
    _strip_prefixes,
)


def _writers_in(sub: list[str], base_dir: str | None = None) -> list[str]:
    """Write targets from ONE sub-command (already split on shell operators)."""
    # 1) Redirections, anywhere in the sub-command: they contribute their own
    # targets and are LIFTED OUT of the word list. Removing them is the half
    # that matters — while they stayed in, a redirection's leftovers were still
    # available to be read as one of the command's arguments.
    targets, sub = split_redirections(sub)
    # The redirection scan above ran over the WHOLE sub-command, prefixes and
    # all — a `>` is a `>` wherever it stands. Identifying the WRITER is what
    # needs the prefixes gone: `sudo tee f` is a `tee`, and the residual
    # boundary called it an uncaught "writer behind a wrapper" when the wrapper
    # was really just the word in front of it.
    sub = _strip_prefixes(sub)
    if not sub:
        return targets
    base = os.path.basename(sub[0]).lower().removesuffix(".exe")
    # Redirections are already gone from `sub`, so a command's own arguments are
    # simply what remains — including any that stood AFTER a redirection, which
    # the old truncation dropped (`cp a >log b` writes `b`). Process
    # substitution still ends the list: it opens a sub-shell whose tokens are
    # not this command's files, and stopping there is what keeps
    # `tee >(cat > x)` from swallowing them (the inner `> x` is still collected
    # by the redirection scan above).
    head: list[str] = []
    for a in sub[1:]:
        # Do NOT break on a bare '(' inside a quoted filename ('Copy (1).txt'):
        # that would drop a legitimate target.
        if a in _PROC_SUB:
            break
        head.append(a)
    nonopt = _positionals(head)
    if base == "tee":
        targets += nonopt  # tee [-a] FILE... — every FILE is written
    elif base == "dd":
        targets += [a[3:] for a in head if a.startswith("of=") and len(a) > 3]
    elif base == "sed":
        targets += _sed_files(head)
    elif base in ("cp", "mv", "install"):
        # `-t DIR` / `--target-directory=DIR` puts the destination in a flag
        # value, and then EVERY positional is a source, not a destination.
        tdir = _opt_value(head, "-t", "--target-directory")
        if tdir is not None:
            targets.append(tdir)
        elif len(nonopt) >= 2:
            targets.append(nonopt[-1])  # trailing positional is the destination
    elif base in ("truncate", "touch"):
        targets += nonopt
    elif base == "curl":
        v = _opt_value(head, "-o", "--output")
        if v is not None:
            targets.append(v)  # curl -O (remote-name) is a documented residual
    elif base == "wget":
        v = _opt_value(head, "-O", "--output-document")
        if v is not None:
            targets.append(v)
    elif base == "tar":
        # only an EXTRACT into an explicit -C DIR (extract-to-cwd is residual).
        extracts = any(
            a in ("-x", "--extract", "--get")
            or (a.startswith("-") and not a.startswith("--") and "x" in a)
            for a in head
        )
        if extracts:
            v = _opt_value(head, "-C", "--directory")
            if v is not None:
                targets.append(v)
    elif base == "unzip":
        v = _opt_value(head, "-d", None)
        if v is not None:
            targets.append(v)
    # 2) interpreter payload: a literal open(path, 'w'/'a'/'x') — inline in the
    # command text, and (see _script_file_writes) inside a script file it runs.
    #
    # Both arms answer to THIS module's idea of a Python interpreter, not to the
    # dangerous-command scanner's `_INTERPRETERS`. Borrowing that set is what
    # made `py` and `python2` dead branches: the constant here claimed a
    # coverage the CALLER did not permit, so the names were listed, believed and
    # never reachable — and the same silence would have swallowed every name
    # added later. `_INTERPRETERS` answers a different question (which programs
    # execute their arguments) for a different gate, and widening it to fix this
    # one would change what that gate scans.
    is_python = _is_python(base)
    if _mentions_interpreter(sub) or is_python:
        targets += _OPEN_RE.findall(" ".join(sub))
    if is_python:
        targets += _script_file_writes(sub, base_dir)
    return targets


# How the answer was reached — see `write_confidence` for what each value means
# and why the vocabulary lives in a module of its own rather than here. Both
# dialect parsers report in these terms, so a consumer can weigh a PowerShell
# answer exactly as it weighs a Bash one. Re-exported: callers have always
# imported these two names from this module.
from write_confidence import (  # noqa: E402,F401 — re-exported
    CONFIDENCE_PARSED,
    CONFIDENCE_REGEX_FALLBACK,
)


def write_targets_with_confidence(
    command: str, base_dir: str | None = None
) -> tuple[list[str], str]:
    """`(targets, confidence)` — see the constants above for what to do with it.

    The widening for a command that CHANGES DIRECTORY lives here, in the twin,
    rather than one floor up in `write_targets`. It was added one floor up and
    that is precisely how the memory-route gate kept the defect after the write
    gate was fixed: this function is the only entry `memory_pretool_block`
    calls, so a repair that lands above it repairs one channel and leaves the
    other reading a script out of a tree the command never enters.

    WHICH directories those are is `shell_roots`' answer, not this module's.
    Confidence comes from the FIRST root — the directory the shell starts in.
    The passes differ only in `base_dir`, which reaches nothing but
    `_script_file_writes`; tokenization sees the same text every time, so a
    later pass cannot be less certain than the first, and merging its verdict
    would be a branch no input can take.
    """
    roots = resolution_roots(command, base_dir)
    cands, confidence = _parse(command, 0, roots[0])
    targets = [t for t in cands if _plausible_path(t)]
    for root in roots[1:]:
        extra_cands, _c = _parse(command, 0, root)
        for extra in extra_cands:
            if _plausible_path(extra) and extra not in targets:
                targets.append(extra)
    return targets, confidence


def _parse(command: str, depth: int, base_dir: str | None = None) -> tuple[list[str], str]:
    """One pass, plus a bounded descent into any shell `-c` payload it carries.

    A payload that fails to tokenize degrades the WHOLE answer to
    `regex_fallback`: the caller is being told how much to trust the list, and
    an uncertain part makes the list uncertain. Reporting `parsed` because the
    outer command parsed would be the more confident of two readings, which is
    the wrong one to hand a consumer that fails closed on uncertainty.
    """
    # File-descriptor numbers are removed from the TEXT, before tokenization,
    # because that is the only place the evidence still exists: `cp a b 2>out`
    # and `cp a b 2 >out` tokenize identically and mean different things, and
    # bash tells them apart by adjacency alone. See `shell_redirection`.
    #
    # Statement boundaries are recovered from the TEXT for the same reason and
    # in the same place: shlex treats a newline as whitespace and drops it, so
    # `_SEPARATORS` could never match the `"\n"` it has always listed. Measured
    # over 9 separator forms x 10 writers: the four newline-only forms lost the
    # real target in 9 of 10 cells each — a MISS, not a phantom. See
    # `shell_statements`.
    stripped = split_statement_breaks(strip_fd_prefixes(_strip_heredocs(command)))
    tokens = tokenize(stripped)
    if tokens is None:
        return _redir_targets_regex(stripped), CONFIDENCE_REGEX_FALLBACK
    cands: list[str] = []
    confidence = CONFIDENCE_PARSED
    for sub in _split_subcommands(tokens):
        cands += _writers_in(sub, base_dir)
        if depth >= _MAX_WRAPPER_DEPTH:
            continue
        for payload in _shell_payloads(sub):
            inner, inner_conf = _parse(payload, depth + 1, base_dir)
            cands += inner
            if inner_conf == CONFIDENCE_REGEX_FALLBACK:
                confidence = CONFIDENCE_REGEX_FALLBACK
    return cands, confidence


def write_targets(command: str, base_dir: str | None = None) -> list[str]:
    """Every path this Bash command appears to write. Best-effort by design.

    Heredoc bodies are stripped before parsing, and tokens carrying a shell
    metacharacter or an unexpanded variable are dropped (unresolvable — the
    documented residual), so a stray `>`/`->`/`$VAR` in prose or a sub-shell
    cannot manufacture a phantom target that blocks a compliant write.

    Confidence-blind on purpose: `bash_write_gate` (QG-0) wants the
    over-detecting answer, and this signature is what it has always returned.
    A caller that cannot afford a false positive asks
    `write_targets_with_confidence` instead.

    Nothing else lives here. Every rule about WHICH paths a command writes —
    the change-of-directory union included — belongs to the twin, so the two
    entry points cannot answer differently about the same command.
    """
    targets, _confidence = write_targets_with_confidence(command, base_dir)
    return targets
