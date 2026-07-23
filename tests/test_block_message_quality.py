"""block-messages-phantom-go-and-platform — remediation the reader can act on.

Two defects, one class: a message that tells the reader to do something they
cannot do.

  * The most-read message in the framework (`task_gate`, fired on every Write
    without an active task) pointed at `/go` — a skill that does not exist.
    Three hooks and one SKILL.md carried the reference.
  * `.tausik/tausik` is not runnable in cmd.exe, and the backslash form is not
    runnable in Git Bash. Measured, not assumed:

        shell        .tausik/tausik      .tausik\\tausik
        cmd.exe      NOT recognized      works
        PowerShell   works               works
        Git Bash     works               NOT (backslash escapes)

    The product audit blamed the missing `.cmd` extension; that turned out to
    be irrelevant (PATHEXT resolves it). The separator is what decides, so the
    choice is per-SHELL, not per-OS.
  * `bash_firewall` told the reader to "ask the user for explicit confirmation
    first" — for a path that was never built. The user says yes and the hook
    blocks identically.

A remediation that cannot be carried out is worse than none: it teaches the
reader that the framework's messages are decorative.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from tausik_utils import cli_invocation  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOKS = _REPO_ROOT / "scripts" / "hooks"
_SKILLS_SRC = _REPO_ROOT / "harness" / "skills"


def _existing_skills() -> set[str]:
    return {p.name for p in _SKILLS_SRC.iterdir() if p.is_dir()}


def _user_facing_strings(source: str) -> str:
    """String literals a USER would read: the args of `print(...)` and the
    message of a raised exception. Docstrings, comments, and URL-building
    literals (`base + "/search"`, a Notion `/search` endpoint in a docstring)
    are developer-facing and excluded — the lint judges advice given to the
    reader, not every slash-token in the file. Returns their concatenation, or
    "" if the file does not parse (a syntax error is another test's job)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    out: list[str] = []

    def _lits(node: ast.AST) -> None:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                out.append(sub.value)

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ):
            for arg in node.args:
                _lits(arg)
        elif isinstance(node, ast.Raise) and node.exc is not None:
            _lits(node.exc)
    return "\n".join(out)


class TestNoPhantomSkillReferences:
    """Every `/skill` a message names must exist, or the advice is a dead end."""

    # A skill reference in this codebase is written one of two prose ways: in a
    # markdown code span (`/plan`) or introduced by an invocation verb (use /go,
    # run /review, try /end). Widening the scan from hooks to all of scripts/
    # (adversarial review, s130-review-fixes) surfaced that a looser matcher
    # floods on URL/route literals — `"/healthz"`, `base + "/search"`, Notion's
    # `/pages` — and on word/word prose like ``None``/unknown. None of those are
    # commands a reader is told to run, and a lint with a dozen false positives
    # gets muted, reproducing the very "hand-maintained list drifts" antipattern
    # this batch criticised. Matching only the two real conventions keeps the
    # `/go`-class catch (both forms below) while excluding paths and word-pairs.
    _SLASH = re.compile(
        r"`/([a-z][a-z0-9-]{1,20})`"  # `/plan`
        r"|(?:\b(?i:use|run|via|try|invoke|or)\s+)/([a-z][a-z0-9-]{1,20})\b"  # Use /go
    )
    # Real commands a reader CAN run — Claude Code built-ins and bundled skills
    # — that are simply not TAUSIK's own skills, so they are not phantoms.
    _BUILTINS = {
        # Claude Code slash built-ins
        "login",
        "logout",
        "help",
        "clear",
        "compact",
        "config",
        "cost",
        "doctor",
        "init",
        "mcp",
        "memory",
        "model",
        "status",
        "terminal-setup",
        "vim",
        "fast",
        # Claude Code bundled skills (present outside harness/skills/)
        "run",
    }

    def _referenced(self, text: str, strip_py_comments: bool = False) -> set[str]:
        if strip_py_comments:
            # The message the reader SEES is the target, not a comment that
            # documents why a phantom reference was removed. Otherwise the lint
            # would forbid explaining the fix in the very file it fixed.
            text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
        found = {m.group(1) or m.group(2) for m in self._SLASH.finditer(text)}
        return found - self._BUILTINS

    def test_scripts_reference_only_existing_skills(self):
        """Not just hooks: gate_*, service_*, project_cli_* emit the majority of
        the CLI-facing text and can carry a phantom `/skill` too (adversarial
        review, s130-review-fixes — the first cut only scanned hooks/)."""
        skills = _existing_skills()
        scripts_root = _REPO_ROOT / "scripts"
        offenders = []
        for path in sorted(scripts_root.rglob("*.py")):
            if path.name.startswith("test_"):
                continue
            # Only strings a USER reads (print args + raised-exception messages)
            # — not docstrings/comments/URL literals, which is where every false
            # positive lived.
            user_text = _user_facing_strings(path.read_text(encoding="utf-8", errors="replace"))
            for name in self._referenced(user_text):
                if name not in skills:
                    offenders.append(f"{path.relative_to(scripts_root).as_posix()}: /{name}")
        assert not offenders, (
            "engine code points at skills that do not exist in harness/skills/ — "
            "the reader follows the advice and nothing happens: " + ", ".join(sorted(offenders))
        )

    def test_skill_docs_reference_only_existing_skills(self):
        skills = _existing_skills()
        offenders = []
        for path in sorted(_SKILLS_SRC.glob("*/SKILL.md")):
            for name in self._referenced(path.read_text(encoding="utf-8", errors="replace")):
                if name not in skills:
                    offenders.append(f"{path.parent.name}/SKILL.md: /{name}")
        assert not offenders, "SKILL.md files reference missing skills: " + ", ".join(
            sorted(offenders)
        )

    def test_the_lint_would_catch_a_phantom(self):
        """Fail-then-pass: prove the matcher fires — `/go` is the exact string
        that shipped for months without anyone noticing."""
        assert "go" in self._referenced("create one with `/plan` or /go.")
        assert "go" not in _existing_skills()

    def test_user_facing_extractor_excludes_docstrings_and_urls(self):
        """The AST scope is load-bearing: it must see print/raise messages and
        NOT docstrings or URL-building literals, or the false positives return."""
        src = (
            '"""A module docstring mentioning the Notion /search endpoint."""\n'
            'BASE = "https://x" + "/search"\n'
            "def f():\n"
            '    print("Run /ghost to proceed")\n'
            '    raise ValueError("try /phantom instead")\n'
        )
        text = _user_facing_strings(src)
        assert "Run /ghost to proceed" in text
        assert "try /phantom instead" in text
        assert "/search endpoint" not in text  # docstring excluded
        refs = self._referenced(text)
        assert refs == {"ghost", "phantom"}

    def test_task_gate_offers_a_command_not_only_a_russian_phrase(self):
        """The English block message used to give a Russian phrase as the only
        way forward, to an audience the README addresses in English."""
        text = (_HOOKS / "task_gate.py").read_text(encoding="utf-8")
        block = text.split("BLOCKED: No active task", 1)[1][:400]
        assert "/plan" in block
        assert "task start" in block


class TestCliInvocation:
    """Per-shell, because no single spelling works everywhere."""

    def test_posix_uses_forward_slashes(self):
        assert cli_invocation(environ={}, os_name="posix") == ".tausik/tausik"

    def test_windows_native_shell_uses_backslash(self):
        """cmd.exe does not recognise `.tausik/tausik` at all."""
        assert cli_invocation(environ={}, os_name="nt") == ".tausik\\tausik"

    @pytest.mark.parametrize(
        "env",
        [
            {"MSYSTEM": "MINGW64"},
            {"MSYS": "winsymlinks:nativestrict"},
            {"SHELL": "/usr/bin/bash"},
        ],
        ids=["mingw", "msys", "posix-shell"],
    )
    def test_windows_posix_shell_uses_forward_slashes(self, env):
        """Git Bash on Windows needs the opposite of cmd — a backslash there is
        an escape character, not a separator."""
        assert cli_invocation(environ=env, os_name="nt") == ".tausik/tausik"

    def test_windows_with_cmd_style_shell_var_stays_native(self):
        """A `SHELL` that is not a POSIX path must not flip the answer."""
        assert cli_invocation(environ={"SHELL": "cmd.exe"}, os_name="nt") == ".tausik\\tausik"

    def test_defaults_read_the_live_environment(self):
        assert cli_invocation() in (".tausik/tausik", ".tausik\\tausik")


class TestGatesUseTheHelper:
    def test_verify_first_remediation_is_not_hardcoded(self):
        import gate_verify_first

        assert gate_verify_first._CLI == cli_invocation()
        src = (_REPO_ROOT / "scripts" / "gate_verify_first.py").read_text(encoding="utf-8")
        assert ".tausik/tausik " not in src

    def test_changelog_gate_remediation_is_not_hardcoded(self):
        import gate_changelog

        assert gate_changelog._CLI == cli_invocation()
        src = (_REPO_ROOT / "scripts" / "gate_changelog.py").read_text(encoding="utf-8")
        assert ".tausik/tausik " not in src


class TestFirewallPromisesOnlyRealEscapes:
    def test_warn_branch_does_not_promise_a_confirmation_path(self):
        """There is no post-confirmation path in `main()`; the message must not
        describe one."""
        src = (_HOOKS / "bash_firewall.py").read_text(encoding="utf-8")
        # Comments may quote the retired wording to explain why it went; what
        # must not survive is the message the USER sees. Strip comment lines
        # before judging, or this test would forbid documenting the fix.
        code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
        assert "ask the user for explicit confirmation first" not in code

    def test_warn_branch_names_the_escape_that_exists(self):
        src = (_HOOKS / "bash_firewall.py").read_text(encoding="utf-8")
        warn_msg = src.split("for regex, reason in WARN_PATTERNS_RE", 1)[1][:900]
        assert "TAUSIK_SKIP_HOOKS" in warn_msg
        # …and that escape must actually be honoured by this hook.
        assert 'os.environ.get("TAUSIK_SKIP_HOOKS")' in src
