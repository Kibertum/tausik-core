#!/usr/bin/env python3
"""Bash write-target parser for `bash_write_gate` (l26-hook-contract-review).

Pure, side-effect-free parsing: given a Bash command string, return the file
paths it appears to write. Split out of `bash_write_gate.py` for the filesize
gate — the enforcement/DB half lives there, the command-parsing half here.

`write_targets(command)` is the public entry point. Everything else is a
best-effort detector for one write vector (redirection, tee, dd, sed -i, cp/mv,
curl/wget/tar/unzip, a literal open() in an interpreter payload). The documented
residual boundary (obfuscation, computed paths) lives in docs/ru/agent-contract.md.
"""

from __future__ import annotations

import os
import re
import shlex
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from bash_firewall import _mentions_interpreter, _split_subcommands  # noqa: E402

# Redirection operators that create/append to a file. Matched against a single
# shlex token, so a '>' living inside a quoted argument ("a > b") is one token
# and never matches — only a bare operator token does. `2>&1` / `>&2` are fd
# dups, not file writes: their target token starts with '&' and is skipped.
_REDIR_RE = re.compile(r"^\d*>>?\|?$|^&>>?$")

# Best-effort catch for a literal open(path, 'w'|'a'|'x') inside an interpreter
# payload. A computed path (variable, concatenation) is the documented residual.
_OPEN_RE = re.compile(
    r"""open\(\s*['"]([^'"]+)['"]\s*,\s*['"][^'"]*[wax]""",
    re.IGNORECASE,
)


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


def _tokenize(command: str) -> list[str] | None:
    """shlex tokens (same recipe as bash_firewall), or None when unparseable."""
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


def _writers_in(sub: list[str]) -> list[str]:
    """Write targets from ONE sub-command (already split on shell operators)."""
    targets: list[str] = []
    # 1) redirections: <op> <target>, anywhere in the sub-command.
    for i, tok in enumerate(sub):
        if _REDIR_RE.match(tok) and i + 1 < len(sub):
            nxt = sub[i + 1]
            if not nxt.startswith("&"):  # '&N' is an fd dup, not a file
                targets.append(nxt)
    if not sub:
        return targets
    base = os.path.basename(sub[0]).lower().removesuffix(".exe")
    # A command's own file arguments come BEFORE any stdout redirection or
    # process substitution. Truncating there stops `tee >(cat > x)` from
    # swallowing the sub-shell's tokens as tee's files (the inner `> x` is still
    # caught by the redirection scan above).
    head: list[str] = []
    for a in sub[1:]:
        # Stop at a redirection or a process-substitution opener (`>(`/`<(` —
        # kept glued by shlex). Do NOT break on a bare '(' inside a quoted
        # filename ('Copy (1).txt'): that would drop a legitimate target.
        if _REDIR_RE.match(a) or a in ("<(", ">("):
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
    # 2) interpreter payload: a literal open(path, 'w'/'a'/'x').
    if _mentions_interpreter(sub):
        targets += _OPEN_RE.findall(" ".join(sub))
    return targets


def write_targets(command: str) -> list[str]:
    """Every path this Bash command appears to write. Best-effort by design.

    Heredoc bodies are stripped before parsing, and tokens carrying a shell
    metacharacter or an unexpanded variable are dropped (unresolvable — the
    documented residual), so a stray `>`/`->`/`$VAR` in prose or a sub-shell
    cannot manufacture a phantom target that blocks a compliant write.
    """
    stripped = _strip_heredocs(command)
    tokens = _tokenize(stripped)
    if tokens is None:
        cands = _redir_targets_regex(stripped)
    else:
        cands = []
        for sub in _split_subcommands(tokens):
            cands += _writers_in(sub)
    return [t for t in cands if _plausible_path(t)]
