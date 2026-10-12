r"""WHAT is dangerous — the policy half of the command firewall.

Split out of `bash_firewall` when a second shell channel appeared. The hook used
to hold three things at once: what counts as dangerous, how to read a POSIX
command line, and what to do about it. That was survivable while POSIX was the
only dialect. It stopped being survivable the moment PowerShell arrived, because
the obvious way to cover a second dialect is to give it its own copy of the
patterns — and a second copy of a rule is how every regression in this
directory's history started (see `rm_wipe_detect`'s header).

So the policy lives here, once, and is applied to whatever the dialect scanners
produce. `bash_firewall` keeps the POSIX scanner and the verdict; the PowerShell
scanner lives in `pwsh_cmd_norm`. Adding a third shell means writing a scanner,
not re-deciding what `git push --force` means.

Every pattern here is matched against SCANNED text — the output of a dialect
scanner, in which a quoted mention has already been reduced to a placeholder.
Matching them against a raw command line would resurrect the false positives
both scanners exist to prevent.
"""

from __future__ import annotations

import os
import re
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from pwsh_write_parse import wiped_root as _pwsh_wiped_root  # noqa: E402
from rm_wipe_detect import (  # noqa: E402
    is_wipe_root,
    normalise_operand,
    wiped_root as _posix_wiped_root,
)

# Patterns that should ALWAYS be blocked — matched against the *command*, not
# against quoted data (see the dialect scanners). The old assumption that these
# strings "are extremely unlikely to appear inside benign commands" turned out
# to be false: journaling the fix for this very bug (`tausik task add --goal
# "... DROP TABLE ..."`) was blocked twice on 2026-07-18.
#
# The `rm` forms that used to live here are NOT substrings — see `wiped_root`.
# Everything left is a phrase whose meaning does not depend on how the command
# around it is spelled, so a substring is the honest test for it: `mkfs.` names
# a program family, `DROP TABLE` is SQL keywords, `dd if=/dev/zero` is one
# idiom. Deliberate, not leftover.
#
# The Windows entries close a channel gap, not a new policy: the POSIX channel
# has blocked `mkfs.` and a raw-device overwrite since the first version, and
# the primary platform's spellings of exactly that were simply absent. A gate
# that names only the other operating system's disk commands is not a lighter
# policy — it is the same policy, unenforced where the project actually runs.
BLOCKED_PATTERNS = [
    ("DROP TABLE", "SQL table drop"),
    ("DROP DATABASE", "SQL database drop"),
    ("TRUNCATE TABLE", "SQL table truncate"),
    (":(){:|:&};:", "Fork bomb"),
    ("mkfs.", "Filesystem format"),
    ("dd if=/dev/zero", "Disk wipe"),
    ("> /dev/sda", "Disk overwrite"),
    ("Format-Volume", "Windows volume format"),
    ("Clear-Disk", "Windows disk wipe"),
    ("Remove-Partition", "Windows partition delete"),
    ("Initialize-Disk", "Windows disk re-initialise"),
    ("vssadmin delete shadows", "Shadow-copy destruction (blocks recovery)"),
]

# Boundary that prefixes a command in a shell line: start of input, or
# any of the shell separators / operators. Mirrors git_push_gate.py.
_CMD_START = r"(?:^|[\s;&|()`])"
# Optional path prefix like `/usr/bin/git` or `./git` or `mygit\`. The
# path component must end with `/` or `\` so a bare token like `gitfoo`
# never matches.
_OPT_PATH = r"(?:[/\w.\\-]*[/\\])?"
# Optional `git -c key=val` flags between `git` and the subcommand.
_OPT_GIT_C = r"(?:\s+-c\s+\S+)*"


def _git_subcmd_re(subcmd: str, danger_arg_re: str) -> re.Pattern:
    """Build a regex that matches `git <subcmd> ... <dangerous-arg>`.

    Preserves git_push_gate's anchor + path-prefix + -c-flag handling.
    Dangerous arg can appear anywhere after the subcommand (including
    after positional args like `git push origin main --force`).

    Both interpolated fragments are wrapped here rather than at the call sites.
    A caller that wrote a bare alternation (`-fd\\b|-df\\b`) handed a top-level
    `|` to this f-string, and that `|` split the WHOLE pattern: those branches
    then ran with no anchor, no path prefix and no `git` in front of them, so
    `ls -df` and `cat notes-df.txt` were both read as a destructive git clean.
    The version that introduced this constructor did so specifically to stop
    `mygit-helper push --force` from false-positiving, and reintroduced the same
    illness one line below. Grouping at the seam means the next pattern cannot
    make that mistake — it is not something each call site must remember.
    """
    # The connector stops at a command separator. `[^\n]*?` did not, so a
    # dangerous-looking argument belonging to the NEXT command could complete a
    # match started by this one (`git clean -n ; tar -fd x`).
    return re.compile(
        rf"{_CMD_START}{_OPT_PATH}git{_OPT_GIT_C}\s+(?:{subcmd})\b[^\n;&|]*?(?:{danger_arg_re})",
        re.IGNORECASE,
    )


# `rm` and everything up to the next command boundary. The dialect scanner has
# already joined sub-commands with ` ; `, so stopping at `;`/`&`/`|` keeps one
# command's operands from being read as another's. `git rm` is excluded by the
# negative lookbehind: it stages a deletion in the index and `git checkout`
# undoes it, so reporting it as "the whole working directory" was simply untrue.
_RM_RE = re.compile(
    rf"{_CMD_START}(?<!git ){_OPT_PATH}rm\b(?P<rest>[^\n;&|]*)",
    re.IGNORECASE,
)


def _posix_rm_wipes_a_root(scanned: str) -> str | None:
    """The tree-root operand of a recursive POSIX `rm`, or None.

    This replaced three literal substrings (`rm -rf /`, `rm -rf /*`, `rm -rf .`)
    that were wrong in BOTH directions at once — they fired on any path that
    merely STARTED that way (`rm -rf .venv`, `rm -rf /tmp/scratch`), and missed
    every spelling of the wipe but one (`rm -fr /` and four others were allowed).

    The first attempt then swapped the substrings for an exact-match set of the
    same four spellings, and an exact match cannot see what a prefix match was
    catching by accident: seven operand spellings that had been blocked stopped
    being blocked. `normalise_operand` answers the question the set was
    pretending to — which place does this operand name — so a spelling that
    resolves to the same tree gets the same verdict.

    Residual, stated rather than left to be discovered: an operand that only
    becomes root-ish after expansion (`$HOME`, `${X:-/}`) is not resolvable
    here and is not claimed to be, and `find / -delete` carries its recursion
    in `find`, where no `rm` operand exists to inspect.
    """
    for match in _RM_RE.finditer(scanned):
        target = _posix_wiped_root(match.group("rest").split())
        if target is not None:
            return target
    return None


# `find` carries the recursion itself: `find / -delete` deletes the whole tree
# with no `rm` operand to inspect, and `find / -exec rm -rf {} \;` hands `rm`
# only the placeholder `{}`. So the root is a START PATH of `find`, judged by the
# SAME `is_wipe_root` the rm detector uses — a second "what is root" would be the
# drift conventions #266/#289 warn against. Documented as this detector's job in
# rm_wipe_detect.py's header and _posix_rm_wipes_a_root above.
_FIND_RE = re.compile(
    rf"{_CMD_START}{_OPT_PATH}find\b(?P<rest>[^\n;&|]*)",
    re.IGNORECASE,
)
# Leading options that precede the path list (`find -L / -delete`).
_FIND_LEADING_OPTS = frozenset({"-h", "-l", "-p", "-d", "-o", "-o0", "-o1", "-o2", "-o3"})
# Actions whose next word is a command; a deleting command there makes the find destructive.
_FIND_EXEC_ACTIONS = frozenset({"-exec", "-execdir", "-ok", "-okdir"})
_DELETING_CMDS = frozenset({"rm", "rmdir", "unlink", "shred"})
# NAME/PATH filters that scope a delete to a named subset. ONLY these downgrade a
# cwd (`.`) delete to "routine" (`find . -name '*.pyc' -delete`). A weaker filter
# (`-type f`, `-mtime`, `-size`) still matches ~everything, so it does NOT — for a
# security verdict, uncertain scoping fails toward blocking (the TAUSIK_SKIP_HOOKS
# escape is recorded). A HARD root (`/`, a drive, `..`) blocks regardless of any
# filter: a filtered subset of the whole filesystem is never a legitimate wipe.
_FIND_NAME_FILTERS = frozenset(
    {
        "-name",
        "-iname",
        "-path",
        "-ipath",
        "-wholename",
        "-iwholename",
        "-regex",
        "-iregex",
        "-lname",
        "-ilname",
        "-samefile",
    }
)


def _find_start_paths(tokens: list[str]) -> list[str]:
    """The path operands of a `find`: leading non-expression tokens after any
    `-H/-L/-P` options, before the first test/action/`(`. Empty → ['.'] (find's
    default search path), so `find -delete` is judged as a cwd wipe."""
    i = 0
    while i < len(tokens) and tokens[i].lower() in _FIND_LEADING_OPTS:
        i += 1
    paths: list[str] = []
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("-") or tok in ("(", "!", ")", ";"):
            break
        paths.append(tok)
        i += 1
    return paths or ["."]


def _find_is_deleting(tokens: list[str]) -> bool:
    """True if the find deletes: `-delete`, or `-exec[dir]/-ok[dir] <rm-like> …`."""
    for idx, tok in enumerate(tokens):
        low = tok.lower()
        if low == "-delete":
            return True
        if low in _FIND_EXEC_ACTIONS and idx + 1 < len(tokens):
            cmd = tokens[idx + 1].replace("\\", "/").rsplit("/", 1)[-1].lower()
            if cmd in _DELETING_CMDS:
                return True
    return False


def _posix_find_wipes_a_root(scanned: str) -> str | None:
    """The root start-path of a deleting `find`, or None.

    Root judged by `is_wipe_root` (shared with rm). Hard roots (`/`, a drive,
    `..`) block whenever the find deletes; the cwd `.` blocks only when the
    delete is NOT scoped by a name/path filter — `find . -name '*.pyc' -delete`
    is the routine dev idiom and stays allowed, mirroring the leniency rm grants
    a non-root operand.

    NOT covered (stated, not silent): a delete driven through a wrapper —
    `find … | xargs rm`, `find … -exec sh -c 'rm …' _ {} +` — where the deleting
    command is behind a pipe or shell, and exec verbs outside rm/rmdir/unlink/shred.
    """
    for match in _FIND_RE.finditer(scanned):
        tokens = match.group("rest").split()
        if not _find_is_deleting(tokens):
            continue
        name_scoped = any(t.lower() in _FIND_NAME_FILTERS for t in tokens)
        for path in _find_start_paths(tokens):
            if not is_wipe_root(path):
                continue
            if normalise_operand(path) == "." and name_scoped:
                continue  # `find . -name '*.pyc' -delete` — routine, not a wipe
            return path
    return None


def wiped_root_any(scanned: str, command: str | None = None) -> str | None:
    """The tree-root operand of a recursive delete in EITHER dialect, or None.

    Named `_any` rather than `wiped_root` on purpose. `rm_wipe_detect.wiped_root`
    takes a TOKEN LIST and parses POSIX flags; this one takes a SCANNED STRING
    and asks both dialects. Two functions with one name and different signatures,
    reachable from the same package, is a trap for the next reader — and this
    module exists because that class of collision is what keeps breaking these
    hooks.

    Both judges run on every command regardless of which tool sent it, and that
    is the point rather than an oversight. A `powershell -Command "Remove-Item
    -Recurse C:\\"` arrives through the Bash tool; a `bash -c 'rm -rf /'`
    arrives through the PowerShell tool. Asking only the judge that matches the
    tool name would reopen the hole one wrapper deep — the exact shape of the
    bypass that closed last session.

    `command` is the RAW line, and the PowerShell judge needs it. The scanners
    join a wrapper's payload back into the scanned text, which drops the quoting
    — that is what lets the POSIX `_RM_RE` read it. But the PowerShell judge is
    STRUCTURAL: it needs `-Command` to still own its argument. After the join,
    `powershell -Command 'Remove-Item -Recurse -Force C:\\'` becomes six bare
    words, `-Command` binds only the next one, and the operand scatters into
    positionals of a statement whose verb is `-Command`. Confirmed allowed
    (rc=0) with the scanned text alone; found by adversarially reviewing this
    fix, not the code it replaced (convention #276).

    Running the structural judge on the raw line cannot resurrect the
    quoted-mention false positive the scanners exist to prevent: a mention
    inside quotes is ONE token to the PowerShell tokenizer, so it never forms a
    `Remove-Item` statement. The POSIX judge is a REGEX and would false-positive
    on exactly that, which is why it is deliberately not given the raw line.
    """
    return (
        _posix_rm_wipes_a_root(scanned)
        or _posix_find_wipes_a_root(scanned)
        or _pwsh_wiped_root(scanned)
        or (_pwsh_wiped_root(command) if command is not None and command != scanned else None)
    )


# Patterns that need confirmation (exit 2 with explanation).
# Each entry: (compiled_regex, human_reason).
WARN_PATTERNS_RE = [
    (
        _git_subcmd_re("reset", r"--hard\b"),
        "git reset --hard discards all local changes permanently",
    ),
    (
        _git_subcmd_re("push", r"(?:--force(?:-with-lease)?\b|--force\b|-f\b)"),
        "git push --force / -f can overwrite remote history",
    ),
    (
        # A flag cluster containing both `f` and `d`, in either order. Written
        # as two lookaheads rather than `-[a-zA-Z]*f[a-zA-Z]*d\b`: that form put
        # two unbounded quantifiers around a literal inside the constructor's
        # own lazy `[^\n]*?`, and the backtracking was super-linear — measured
        # 0.009s / 0.23s / 3.55s on `git clean -` followed by 1k / 5k / 20k
        # `f`s. Every shell tool call goes through this hook, so that is a stall
        # of the whole session, reachable from one ordinary-looking line. Each
        # lookahead here scans forward once and fails fast.
        # Second branch: the flags written apart (`git clean -f -d`), which the
        # single-cluster form never matched. That gap was asserted closed in a
        # closed task's evidence and was not — the same "one spelling blocked,
        # the rest allowed" shape this file keeps producing.
        _git_subcmd_re(
            "clean",
            r"-(?=[a-zA-Z]*f)(?=[a-zA-Z]*d)[a-zA-Z]+\b"
            r"|-(?=[a-zA-Z]*f)[a-zA-Z]+\b[^\n;&|]{0,80}?-(?=[a-zA-Z]*d)[a-zA-Z]+\b",
        ),
        "git clean -fd removes untracked files permanently",
    ),
    (
        _git_subcmd_re("checkout", r"--\s+\."),
        "git checkout -- . discards all unstaged changes",
    ),
]
