"""Tests for scripts/hooks/bash_write_gate.py (l26-hook-contract-review).

Two layers:
  * write_targets() — the write-vector parser, unit-tested for both the
    catches (redirection, tee, dd, sed -i, cp/mv, touch, python open) and the
    non-catches that would be false positives (fd dup, quoted '>', read-only).
  * the hook end-to-end — QG-0 (no active task) and scope-ACL parity with the
    Write gate, plus out-of-tree jurisdiction and TAUSIK_SKIP_HOOKS.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys

import pytest
from conftest import canonical_ddl

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
_HOOKS = os.path.join(_SCRIPTS, "hooks")
if _HOOKS not in sys.path:
    sys.path.insert(0, _HOOKS)

from bash_write_gate import write_targets  # noqa: E402

HOOK = os.path.join(_HOOKS, "bash_write_gate.py")


class TestWriteTargets:
    @pytest.mark.parametrize(
        "command,expected",
        [
            # --- redirections (the demonstrated heredoc vector) ---
            ("echo hi > out.txt", ["out.txt"]),
            ("echo hi >> out.txt", ["out.txt"]),
            ("cat > f.py <<EOF\nprint(1)\nEOF", ["f.py"]),
            ("echo hi >out.txt", ["out.txt"]),  # no space
            ("cmd 2> err.log", ["err.log"]),  # stderr to file IS a write
            # --- writer programs ---
            ("echo x | tee a.txt b.txt", ["a.txt", "b.txt"]),
            ("dd if=src of=out.bin", ["out.bin"]),
            ("sed -i 's/a/b/' file.py", ["file.py"]),
            ("sed -i -e 's/a/b/' file.py", ["file.py"]),
            ("cp a.py b.py", ["b.py"]),
            ("mv a.py b.py", ["b.py"]),
            ("touch new.py", ["new.py"]),
            ("python -c \"open('gen.py','w').write('x')\"", ["gen.py"]),
            ("python - <<'PY'\nfrom pathlib import Path\nPath('gen.py').write_text('x')\nPY", ["gen.py"]),
            ("python - <<'PY'\nfrom pathlib import Path\nPath('gen.py').read_text()\nPY", []),
            # --- review fixes: cp/mv -t, curl/wget/tar/unzip, BSD sed -i '' ---
            ("cp -t scripts/hooks a.txt", ["scripts/hooks"]),
            ("cp --target-directory=scripts/hooks a.txt b.txt", ["scripts/hooks"]),
            ("mv -t dest src.py", ["dest"]),
            ("curl -o out.py https://example/x", ["out.py"]),
            ("wget -O out.py https://example/x", ["out.py"]),
            ("tar -xzf a.tar.gz -C scripts/hooks", ["scripts/hooks"]),
            ("unzip a.zip -d scripts/hooks", ["scripts/hooks"]),
            ("sed -i '' 's/a/b/' file.txt", ["file.txt"]),  # BSD -i EXT form
            # heredoc header write is caught; a '->' in its BODY is NOT a target
            ("cat > scripts/x.py <<'EOF'\ndef f() -> int:\n    return 1\nEOF\n", ["scripts/x.py"]),
            # process substitution: the real inner write is caught, no phantom
            ("diff a b | tee >(cat > x.txt)", ["x.txt"]),
            # round-2 regression: a QUOTED filename with (), &, > survives shlex
            # as one token (proof it was quoted) — must NOT be dropped.
            ("echo hi > 'file (draft).txt'", ["file (draft).txt"]),
            ("cp a.txt 'Copy (1).docx'", ["Copy (1).docx"]),
            ("sed -i 's/a/b/' 'notes (old).md'", ["notes (old).md"]),
            ("dd if=src of='backup(1).bin'", ["backup(1).bin"]),
            ("echo hi > 'Q&A.md'", ["Q&A.md"]),
            ("touch 'a & b.txt'", ["a & b.txt"]),
            ("cp -- -a.txt b.txt", ["b.txt"]),  # -- ends option parsing
            # plain `<<EOF` requires an EXACT terminator: an indented `    EOF`
            # in the body must NOT end the scan early and re-expose body text.
            ("cat > f.py <<EOF\nx\n    EOF\ny -> z\nEOF\n", ["f.py"]),
            # `<<-EOF` strips leading TABS from the terminator (tab-indented EOF).
            ("cat > f.py <<-EOF\n\tbody -> x\n\tEOF\n", ["f.py"]),
            # multiple heredocs on one header line: BOTH bodies stripped, the
            # real redirect target still detected.
            ("cat > out.txt <<A <<B\nx > y\nA\nz -> w\nB\n", ["out.txt"]),
            # sed with `--` before a dash-prefixed filename.
            ("sed -i 's/a/b/' -- -weird.txt", ["-weird.txt"]),
            ("sed -i -- 's/a/b/' file.txt", ["file.txt"]),
        ],
    )
    def test_detected(self, command, expected):
        assert write_targets(command) == expected

    @pytest.mark.parametrize(
        "command",
        [
            "ls -la",  # no write
            "cat file.txt",  # read
            "cmd 2>&1",  # fd dup, not a file
            "grep foo bar.py",
            'echo "a > b"',  # '>' is quoted payload, not a redirection
            "python -m pytest",  # interpreter, no open()
            "sed 's/a/b/' file.py",  # no -i: not in-place, no write
            "grep \"open('x','w')\" f.py",  # open() in non-interpreter payload
            # --- review fixes: heredoc body / vars / documented residuals ---
            "cat <<'EOF'\nthis line mentions a > b in prose\nEOF",  # body '>' is not a redirect
            "cat <<'EOF'\ndef f() -> int: pass\nEOF",  # arrow in body, pure stdout
            "cat <<'EOF'\ndon't forget x > y later\nEOF",  # apostrophe + '>' in body
            "echo x > $SCRATCH/probe.py",  # unexpanded var — unresolvable, not in-tree
            "curl -O https://example/y.py",  # -O remote-name is documented residual
            # multi-heredoc, no redirect: the SECOND body must not leak a phantom
            "cat <<A <<B\nbodyA has a > b\nA\nbodyB has -> c\nB\n",
        ],
    )
    def test_not_detected(self, command):
        assert write_targets(command) == []

    def test_multiple_subcommands(self):
        # each sub-command judged independently; both writes surface
        assert write_targets("echo a > x.txt && echo b >> y.txt") == ["x.txt", "y.txt"]


def _make_db(tmp_path, tasks):
    """tasks: [(slug, status, scope_paths_json_or_None)]"""
    tausik = tmp_path / ".tausik"
    tausik.mkdir(exist_ok=True)
    db = tausik / "tausik.db"
    conn = sqlite3.connect(str(db))
    conn.execute(canonical_ddl("tasks"))
    conn.executemany(
        "INSERT INTO tasks (slug, title, status, scope_paths, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
        [(slug, slug, status, paths) for slug, status, paths in tasks],
    )
    conn.commit()
    conn.close()
    return str(db)


def _run_hook(project_dir, command, env_extra=None):
    env = os.environ.copy()
    env["TAUSIK_SKIP_HOOKS"] = ""
    env["TAUSIK_HOOK_FAIL_SECURE"] = ""
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    if env_extra:
        env.update(env_extra)
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=10,
    )


class TestHook:
    def test_no_active_task_bash_write_blocked(self, tmp_path):
        # QG-0 parity: a Bash write with no active task is blocked, exactly as
        # a Write would be. This is the demonstrated bypass.
        _make_db(tmp_path, [("t1", "done", None)])
        r = _run_hook(tmp_path, "echo x > scripts/a.py")
        assert r.returncode == 2
        assert "No active task" in r.stderr

    def test_no_active_task_out_of_tree_allowed(self, tmp_path):
        _make_db(tmp_path, [("t1", "done", None)])
        outside = tmp_path.parent / "elsewhere.txt"
        r = _run_hook(tmp_path, f'echo x > "{outside}"')
        assert r.returncode == 0, r.stderr

    def test_no_write_command_allowed(self, tmp_path):
        _make_db(tmp_path, [("t1", "done", None)])
        r = _run_hook(tmp_path, "python -m pytest -q")
        assert r.returncode == 0, r.stderr

    def test_active_task_write_inside_scope_allowed(self, tmp_path):
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        r = _run_hook(tmp_path, "echo x > scripts/a.py")
        assert r.returncode == 0, r.stderr

    def test_active_task_write_outside_scope_blocked(self, tmp_path):
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        r = _run_hook(tmp_path, "echo x > docs/a.md")
        assert r.returncode == 2
        assert "SENAR Rule 2" in r.stderr and "t1" in r.stderr

    def test_pathlib_python_stdin_write_outside_scope_is_blocked(self, tmp_path):
        """The live bypass: `python - <<PY` must reach the shared AST reader."""
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        command = "python - <<'PY'\nfrom pathlib import Path\nPath('harness/x.py').write_text('x')\nPY"
        result = _run_hook(tmp_path, command)
        assert result.returncode == 2, result.stderr
        assert "harness/x.py" in result.stderr

    def test_active_undeclared_task_write_allowed(self, tmp_path):
        # No scope declared anywhere -> legacy freedom (QG-0 already satisfied).
        _make_db(tmp_path, [("t1", "active", None)])
        r = _run_hook(tmp_path, "echo x > anywhere/a.py")
        assert r.returncode == 0, r.stderr

    def test_heredoc_outside_scope_blocked(self, tmp_path):
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        r = _run_hook(tmp_path, "cat > docs/x.md <<EOF\nhello\nEOF")
        assert r.returncode == 2

    def test_heredoc_body_arrow_does_not_block_inscope_write(self, tmp_path):
        # Regression (review HIGH): a '->' in the heredoc BODY must not spawn a
        # phantom target that blocks a fully in-scope write.
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        r = _run_hook(tmp_path, "cat > scripts/x.py <<'EOF'\ndef f() -> int:\n    return 1\nEOF\n")
        assert r.returncode == 0, r.stderr

    def test_cp_target_directory_into_gated_dir_blocked(self, tmp_path):
        # Regression (review CRITICAL): cp --target-directory= must be caught.
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        r = _run_hook(tmp_path, "cp --target-directory=docs a.txt")
        assert r.returncode == 2, r.stderr

    def test_var_path_not_treated_as_in_tree(self, tmp_path):
        # Regression (review MEDIUM): an unexpanded $VAR target is unresolvable
        # and must not be forced in-tree and blocked.
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        r = _run_hook(tmp_path, "echo x > $SCRATCH/probe.py")
        assert r.returncode == 0, r.stderr

    def test_quoted_paren_filename_still_gated(self, tmp_path):
        # Regression (review round-2 CRITICAL): a quoted filename containing
        # '(' must NOT silently bypass the scope gate.
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        r = _run_hook(tmp_path, "echo x > 'docs/backdoor (v2).py'")
        assert r.returncode == 2, r.stderr

    def test_skip_env_bypasses(self, tmp_path):
        _make_db(tmp_path, [("t1", "done", None)])
        r = _run_hook(
            tmp_path,
            "echo x > scripts/a.py",
            env_extra={"TAUSIK_SKIP_HOOKS": "1"},
        )
        assert r.returncode == 0

    def test_no_tausik_dir_allowed(self, tmp_path):
        r = _run_hook(tmp_path, "echo x > scripts/a.py")
        assert r.returncode == 0


class TestShellWrapperRecursion:
    """`bash -c 'cmd > file'` — the wrapper that used to hide every target.

    Rule 1 and the scope ACL were bypassable by a one-liner of the same class
    Decision #162 closed for heredocs, while the documented residual claimed the
    bar had been raised to "must actively obfuscate". `bash -c` is an everyday
    form, not obfuscation.
    """

    def _wt(self):
        import sys as _sys

        hooks = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "hooks"
        )
        if hooks not in _sys.path:
            _sys.path.insert(0, hooks)
        from bash_write_parse import write_targets

        return write_targets

    @pytest.mark.parametrize(
        "command,expected",
        [
            ("bash -c 'printf x > scripts/foo.py'", ["scripts/foo.py"]),
            ('sh -c "echo x > a.py"', ["a.py"]),
            ("bash -lc 'echo x > b.py'", ["b.py"]),  # combined short flags
            ("bash -ec 'echo x > c.py'", ["c.py"]),
            ("zsh -c 'tee d.py'", ["d.py"]),  # a writer, not a redirect
            ("dash -c 'sed -i s/a/b/ e.py'", ["e.py"]),
            ("bash -c \"bash -c 'echo x > f.py'\"", ["f.py"]),  # nested wrapper
        ],
    )
    def test_payload_targets_are_found(self, command, expected):
        assert self._wt()(command) == expected

    @pytest.mark.parametrize(
        "command",
        [
            "bash --version",
            "bash script.sh",  # no -c: the arg is a file to RUN
            "bash -c 'pytest -q'",  # payload writes nothing
            "echo 'bash -c \"x > y\"'",  # a quoted MENTION is not a write
            "bash --color=auto -c 'pytest -q'",  # long option is not a short cluster
            "python -m pytest -q",
        ],
    )
    def test_no_false_positive(self, command):
        assert self._wt()(command) == []

    def test_recursion_is_bounded(self):
        # Four levels: the innermost sits past _MAX_WRAPPER_DEPTH and is not
        # descended into. The bound is a stated constant, so exceeding it is a
        # decision rather than a RecursionError.
        import sys as _sys

        hooks = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "hooks"
        )
        if hooks not in _sys.path:
            _sys.path.insert(0, hooks)
        from bash_write_parse import _MAX_WRAPPER_DEPTH

        assert _MAX_WRAPPER_DEPTH >= 2
        cmd = "echo x > deep.py"
        for _ in range(_MAX_WRAPPER_DEPTH + 2):
            cmd = f'bash -c "{cmd}"'
        self._wt()(cmd)  # must return, not recurse forever

    def test_unparseable_payload_degrades_the_whole_confidence(self):
        import sys as _sys

        hooks = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "hooks"
        )
        if hooks not in _sys.path:
            _sys.path.insert(0, hooks)
        from bash_write_parse import CONFIDENCE_REGEX_FALLBACK, write_targets_with_confidence

        # Outer tokenizes, payload does not. Answering `parsed` would be the
        # more confident of two readings — the wrong one for a caller that
        # fails closed on uncertainty.
        _t, conf = write_targets_with_confidence('bash -c "awk \'{print $1} > x.py"')
        assert conf == CONFIDENCE_REGEX_FALLBACK


class TestTransparentCommandPrefixes:
    """`env bash -c '…'` — the wrapper hidden by the word in front of it.

    Found by adversarially reviewing the `bash -c` FIX (convention #276), not
    the code it replaced: the shell test read `sub[0]`, which is `env`, so the
    same one-line bypass survived one level further out.
    """

    def _wt(self):
        import sys as _sys

        hooks = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "hooks"
        )
        if hooks not in _sys.path:
            _sys.path.insert(0, hooks)
        from bash_write_parse import write_targets

        return write_targets

    @pytest.mark.parametrize(
        "command,expected",
        [
            ("env bash -c 'echo x > e.py'", ["e.py"]),
            ("env FOO=1 BAR=2 bash -c 'echo x > f.py'", ["f.py"]),
            ("sudo bash -c 'echo x > g.py'", ["g.py"]),
            ("nohup bash -c 'echo x > h.py'", ["h.py"]),
            ("timeout 5 bash -c 'echo x > i.py'", ["i.py"]),
            ("timeout 30s sh -c 'echo x > j.py'", ["j.py"]),
            # The residual boundary named `sudo tee` as an uncaught "writer
            # behind a wrapper". The writer was never hidden by `tee`.
            ("sudo tee k.py", ["k.py"]),
            ("nice -n 5 tee l.py", ["l.py"]),
            ("sudo sed -i s/a/b/ m.py", ["m.py"]),
        ],
    )
    def test_prefixed_writes_are_found(self, command, expected):
        assert self._wt()(command) == expected

    @pytest.mark.parametrize(
        "command",
        [
            "env",
            "sudo -v",
            "timeout --help",
            "nice",
            "python environment.py",  # a NAME that starts like a prefix
            "./timeout_test.sh",
            "env bash -c 'pytest -q'",  # prefix + wrapper, payload writes nothing
            "exec pytest -q",
        ],
    )
    def test_no_false_positive(self, command):
        assert self._wt()(command) == []

    def test_remaining_boundary_is_pinned_not_assumed(self):
        # NOT closed here, and pinned so the day it is, the change announces
        # itself instead of passing silently (memory #292 — the pattern that
        # already paid off once this session).
        #
        # AND IT ANNOUNCED ITSELF. `xargs` was pinned here as open and is now
        # closed (session #238, xargs-executes-its-arguments): it turned out to
        # be an ordinary wrapper, and adding it to `_WRAPPER_VALUE_FLAGS` made
        # the command behind it visible. The pin did exactly its job — this
        # assertion went red on the commit that closed the gap rather than
        # letting it pass unnoticed. Its evidence now lives in
        # `tests/test_xargs_hides_the_command.py`.
        #
        # `ssh` STAYS pinned as open, and for a reason `xargs` never had: its
        # payload runs on ANOTHER HOST, where this project's paths mean nothing.
        wt = self._wt()
        assert wt("echo f.py | xargs -I{} bash -c 'echo x > {}'") == ["{}"], (
            "the xargs gap reopened, or the placeholder stopped being reported — "
            "the second would let an unknown write pass silently"
        )
        assert wt("ssh host 'echo x > /remote/f.py'") == []


class TestWriteFromInsideAScriptFile:
    """The write is in the SCRIPT, not in the command text.

    Session #200 measured both halves of this on the same path: `cp x
    .claude/mcp/project/tools_spec.py` was refused with the ACL printed, and
    `python helper.py` writing that same path returned zero and made the edit.
    The gate's own docstring called that gap "obfuscated writes" and claimed the
    bar was "must actively obfuscate" — but running a script from a file is the
    ordinary way to run code. A gate that overstates what it prevents is worse
    than one that prevents less: the agent reading the refusal concludes the ACL
    is closed.
    """

    @staticmethod
    def _script(tmp_path, body):
        """Returns a PROJECT-RELATIVE name, and that is not incidental.

        An absolute Windows path inside a Bash command loses its backslashes
        to posix tokenisation, so the parser would look for a file that is not
        there, degrade softly, and the test would pass or fail for a reason
        having nothing to do with the gate. The measured command in #200 was
        `python /tmp/edit2.py` — a slash path — and this is the shape agents
        actually write.
        """
        (tmp_path / "helper.py").write_text(body, encoding="utf-8")
        return "helper.py"

    def test_a_write_from_a_script_is_blocked_like_a_direct_write(self, tmp_path):
        """AC3 — the negative scenario, run through the REAL hook.

        Not a unit test on the parser: this is the same subprocess invocation
        that returned zero when it was measured, so a fix that only satisfies a
        parser assertion cannot pass it.
        """
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        script = self._script(tmp_path, 'open("harness/x.py", "w").write("x")\n')
        r = _run_hook(tmp_path, "python " + script)
        assert r.returncode == 2, r.stderr
        assert "harness/x.py" in r.stderr
        assert "declared scope" in r.stderr

    def test_a_write_from_a_script_inside_the_acl_is_allowed(self, tmp_path):
        """The green branch, and it is measured: the ONLY difference from the
        test above is which path the script writes, so a gate that blocked
        every `python <script>` would fail here."""
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        script = self._script(tmp_path, 'open("scripts/x.py", "w").write("x")\n')
        r = _run_hook(tmp_path, "python " + script)
        assert r.returncode == 0, r.stderr

    def test_no_active_task_is_blocked_too(self, tmp_path):
        """QG-0 parity — the rule the direct-write path already enforced."""
        _make_db(tmp_path, [("t1", "done", None)])
        script = self._script(tmp_path, 'open("scripts/a.py", "w").write("x")\n')
        r = _run_hook(tmp_path, "python " + script)
        assert r.returncode == 2, r.stderr
        assert "No active task" in r.stderr

    def test_dash_m_does_not_read_its_argument_as_a_script(self, tmp_path):
        """`python -m pytest tests/test_x.py` must not be blocked by literal
        open(..., "w") calls INSIDE that test file — the command runs none of
        them. This is the false block the narrow rule exists to prevent, and it
        is the reason `-m` is refused a script rather than merely deprioritised."""
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        target = tmp_path / "tests"
        target.mkdir()
        (target / "test_x.py").write_text('open("harness/y.py", "w")\n', encoding="utf-8")
        r = _run_hook(tmp_path, "python -m pytest tests/test_x.py")
        assert r.returncode == 0, r.stderr

    def test_an_absent_script_degrades_softly(self, tmp_path):
        """Fail-soft, and the asymmetry is deliberate: a miss leaves the gate
        where it stood, a false block stops the work."""
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        r = _run_hook(tmp_path, "python nope.py")
        assert r.returncode == 0, r.stderr


class TestScriptFileParserBoundaries:
    """Unit-level, on the parser, for the limits the hook tests cannot show."""

    def test_an_oversized_script_is_not_read(self, tmp_path, monkeypatch):
        import bash_write_parse as P

        big = tmp_path / "big.py"
        big.write_text(
            'open("harness/x.py", "w")\n' + ("# pad\n" * 60000),
            encoding="utf-8",
        )
        assert big.stat().st_size > P._MAX_SCRIPT_BYTES
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        assert P._script_file_writes(["python", str(big)]) == []

    def test_a_script_just_under_the_cap_is_read(self, tmp_path, monkeypatch):
        """Pairs with the test above: without it, a cap of zero would pass."""
        import bash_write_parse as P

        small = tmp_path / "small.py"
        small.write_text('open("harness/x.py", "w")\n', encoding="utf-8")
        assert small.stat().st_size < P._MAX_SCRIPT_BYTES
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        assert P._script_file_writes(["python", str(small)]) == ["harness/x.py"]

    def test_a_non_python_interpreter_is_not_claimed_to_be_read(self, tmp_path, monkeypatch):
        """`python_source_writes` reads Python. A parser that cannot read a
        substrate must not report on it — the shell and Node cases stay in the
        declared residual."""
        import bash_write_parse as P

        js = tmp_path / "w.js"
        js.write_text('fs.writeFileSync("harness/x.py", "x")\n', encoding="utf-8")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        assert P._script_file_writes(["node", str(js)]) == []


# Every ordinary way to say "run this Python script". The gate used to hold on
# `python` and `python3` alone; each of the others was measured ALLOWED through
# the real hook in session #203 with the script writing outside the ACL.
_INTERPRETER_FORMS = [
    "python {s}",
    "python3 {s}",
    "python3.11 {s}",
    "python3.12 {s}",
    "python2 {s}",
    "pythonw {s}",
    "py {s}",
    "py -3 {s}",
    "py -3.11 {s}",
    "python.exe {s}",
]

# The same command, with a flag somewhere other than where the first fix looked.
# A trailing `-m`/`-c` is an argument to the SCRIPT, not to the interpreter, and
# reading it as the latter disarmed the gate on an everyday command line.
_FLAG_POSITION_FORMS = [
    "python {s} -m foo",
    "python {s} --mode -c",
    "python {s} -c",
    "python -u {s}",
    "python -W ignore {s}",
    "python -X dev {s}",
    "python -- {s}",
]

_RUNS_A_SCRIPT = _INTERPRETER_FORMS + _FLAG_POSITION_FORMS

# `-m`/`-c` in OPTION position — before the first positional — really does mean
# there is no script file. Every spelling of it, including the glued and the
# clustered short forms, which the exact-token set did not cover.
_RUNS_NO_SCRIPT = [
    "python -m pytest tests/test_x.py",
    "python -mpytest tests/test_x.py",
    "python -um pytest tests/test_x.py",
    "python3.11 -m pytest tests/test_x.py",
    "py -3 -m pytest tests/test_x.py",
]


class TestNeighbouringFormsOfRunningAScript:
    """The defect of `write-gate-parses-command-text-not-writes` (#201).

    That task closed the form it MEASURED — `python script.py` — and left the
    neighbours: one trailing token, or a versioned interpreter name, and the
    same write went through. Measured, not read: 10 of 17 forms returned exit 0
    with the script writing outside the ACL, and both of the gate's rules fell
    together (SENAR Rule 2 and the QG-0 "no active task" refusal).

    Parametrised on purpose. A per-form test is a per-form promise, and this is
    the second visit to this file for exactly the sin of promising coverage of
    a SHAPE while testing one spelling of it (memory #495).
    """

    @staticmethod
    def _script(tmp_path, body):
        (tmp_path / "helper.py").write_text(body, encoding="utf-8")
        return "helper.py"

    @pytest.mark.parametrize("form", _RUNS_A_SCRIPT)
    def test_out_of_scope_write_is_blocked_in_every_form(self, tmp_path, form):
        """AC2 — SENAR Rule 2 holds however the interpreter is spelled."""
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        script = self._script(tmp_path, 'open("harness/x.py", "w").write("x")\n')
        r = _run_hook(tmp_path, form.format(s=script))
        assert r.returncode == 2, f"{form}: {r.stderr}"
        assert "harness/x.py" in r.stderr

    @pytest.mark.parametrize("form", _RUNS_A_SCRIPT)
    def test_no_active_task_is_blocked_in_every_form(self, tmp_path, form):
        """AC11 — the OTHER rule the same hole disarmed. Measured separately
        because a fix that only restored the ACL check would leave QG-0 open,
        and the two failed together, so they must be shown to hold together."""
        _make_db(tmp_path, [("t1", "done", None)])
        script = self._script(tmp_path, 'open("harness/x.py", "w").write("x")\n')
        r = _run_hook(tmp_path, form.format(s=script))
        assert r.returncode == 2, f"{form}: {r.stderr}"
        assert "No active task" in r.stderr

    @pytest.mark.parametrize("form", _RUNS_A_SCRIPT)
    def test_in_scope_write_is_allowed_in_every_form(self, tmp_path, form):
        """AC3 — the green branch, and it has to be MEASURED to mean anything.

        The only difference from the test above is the path the script writes,
        so a parser widened into blocking every `python <anything>.py` fails
        here. Before the fix this was green for the wrong reason — green
        because nothing was checked at all (memory #491)."""
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        script = self._script(tmp_path, 'open("scripts/x.py", "w").write("x")\n')
        r = _run_hook(tmp_path, form.format(s=script))
        assert r.returncode == 0, f"{form}: {r.stderr}"

    @pytest.mark.parametrize("command", _RUNS_NO_SCRIPT)
    def test_no_script_flag_in_option_position_reads_nothing(self, tmp_path, command):
        """AC4 — and two of these were ALREADY false-blocking before this task.

        `python -mpytest tests/test_x.py` and `python -um pytest tests/test_x.py`
        returned exit 2 on the measured baseline: the exact-token set {-m, -c}
        did not recognise the glued or clustered spelling, so the parser fell
        through to the first `.py` positional and reported literal open() calls
        out of a file the command never writes."""
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        target = tmp_path / "tests"
        target.mkdir(exist_ok=True)
        (target / "test_x.py").write_text('open("harness/y.py", "w")\n', encoding="utf-8")
        r = _run_hook(tmp_path, command)
        assert r.returncode == 0, f"{command}: {r.stderr}"

    def test_the_script_is_the_first_positional_not_the_first_py_file(self, tmp_path):
        """A `.py` file further down the line is an ARGUMENT, not the script.

        An extensionless Python entry point is not exotic — this repository's
        own CLI is one (`.tausik/tausik`) — so `python <entrypoint>
        tests/test_x.py` is an ordinary command here. Taking the first
        positional that merely ENDS in .py reads the test file instead and
        reports literal open() calls the command never performs.

        Added because the mutation for this rule SURVIVED: the option walk
        already covered every other measured form, so the rule was correct and
        unmeasured — the same "declared but unreachable" shape this task exists
        to remove (memory #492)."""
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        (tmp_path / "entrypoint").write_text("import sys\n", encoding="utf-8")
        target = tmp_path / "tests"
        target.mkdir(exist_ok=True)
        (target / "test_x.py").write_text('open("harness/y.py", "w")\n', encoding="utf-8")
        r = _run_hook(tmp_path, "python entrypoint tests/test_x.py")
        assert r.returncode == 0, r.stderr


class TestRedirectionDoesNotDisplaceTheDestination:
    """write-gate-takes-a-file-descriptor-number-as-a-write-target, end to end.

    The parser-level sweep lives in `test_shell_redirection`. What is proved
    HERE is the part a parser test cannot reach: the verdict the hook actually
    returns, and the path it names when it refuses. Both were wrong, and the
    second one silently: the block on `cp a docs/x.md 2>/dev/null` was correct
    only because the phantom `2` happened to be out of scope too, and it sent
    whoever read it to a file named `2` that no command was writing.
    """

    IN_SCOPE = "scripts/a.py"
    OUT_OF_SCOPE = "docs/a.md"

    REDIRECTS = ["2>/dev/null", "2> /dev/null", "1>log", "2>>log", "3>trace", "2>&1", "&>log"]

    @pytest.mark.parametrize("redirect", REDIRECTS)
    @pytest.mark.parametrize("writer", ["cp", "mv", "install -m 644"])
    def test_destination_in_scope_is_allowed_under_any_redirection(
        self, tmp_path, writer, redirect
    ):
        """The live false block from session #203: the destination is inside the
        declared scope, and the command was refused anyway — on the descriptor."""
        _make_db(tmp_path, [("t1", "active", '["scripts/", "log", "trace"]')])
        r = _run_hook(tmp_path, f"{writer} src {self.IN_SCOPE} {redirect}")
        assert r.returncode == 0, r.stderr

    @pytest.mark.parametrize("redirect", REDIRECTS)
    @pytest.mark.parametrize("writer", ["cp", "mv", "install -m 644"])
    def test_destination_out_of_scope_is_refused_by_name(self, tmp_path, writer, redirect):
        """Right verdict AND right reason. The path in the message is the one
        the command writes, never the descriptor number."""
        _make_db(tmp_path, [("t1", "active", '["scripts/", "log", "trace"]')])
        r = _run_hook(tmp_path, f"{writer} src {self.OUT_OF_SCOPE} {redirect}")
        assert r.returncode == 2
        assert self.OUT_OF_SCOPE in r.stderr
        offending = r.stderr.split("Active ACL(s):")[0]
        assert "\n  2\n" not in offending and "\n  1\n" not in offending

    @pytest.mark.parametrize("redirect", REDIRECTS)
    def test_qg0_names_the_destination_when_no_task_is_active(self, tmp_path, redirect):
        _make_db(tmp_path, [("t1", "done", None)])
        r = _run_hook(tmp_path, f"cp src {self.IN_SCOPE} {redirect}")
        assert r.returncode == 2
        assert "No active task" in r.stderr
        # The QG-0 branch prints the path with the OS separator; only the
        # Rule 2 branch normalises to '/'. Compare on the normalised form —
        # what is under test is WHICH path is named, not how it is spelled.
        assert self.IN_SCOPE in r.stderr.replace("\\", "/")

    def test_a_file_actually_named_2_is_still_gated(self, tmp_path):
        """The fix must not buy its silence by ignoring digits: `cp a 2 >out`
        writes a file named `2`, and that is a write like any other."""
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        r = _run_hook(tmp_path, "cp src 2 >scripts/log")
        assert r.returncode == 2
        assert "SENAR Rule 2" in r.stderr

    def test_input_redirection_target_is_not_reported_as_written(self, tmp_path):
        """`cp a b <in` reported `in` — a file it only READS — and lost `b`."""
        _make_db(tmp_path, [("t1", "active", '["scripts/"]')])
        r = _run_hook(tmp_path, f"cp {self.OUT_OF_SCOPE} {self.IN_SCOPE} <{self.OUT_OF_SCOPE}")
        assert r.returncode == 0, r.stderr
