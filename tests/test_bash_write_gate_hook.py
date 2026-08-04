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

        hooks = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "hooks")
        if hooks not in _sys.path:
            _sys.path.insert(0, hooks)
        from bash_write_parse import write_targets

        return write_targets

    @pytest.mark.parametrize(
        "command,expected",
        [
            ("bash -c 'printf x > scripts/foo.py'", ["scripts/foo.py"]),
            ('sh -c "echo x > a.py"', ["a.py"]),
            ("bash -lc 'echo x > b.py'", ["b.py"]),          # combined short flags
            ("bash -ec 'echo x > c.py'", ["c.py"]),
            ("zsh -c 'tee d.py'", ["d.py"]),                  # a writer, not a redirect
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
            "bash script.sh",                       # no -c: the arg is a file to RUN
            "bash -c 'pytest -q'",                  # payload writes nothing
            "echo 'bash -c \"x > y\"'",             # a quoted MENTION is not a write
            "bash --color=auto -c 'pytest -q'",     # long option is not a short cluster
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

        hooks = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "hooks")
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

        hooks = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "hooks")
        if hooks not in _sys.path:
            _sys.path.insert(0, hooks)
        from bash_write_parse import CONFIDENCE_REGEX_FALLBACK, write_targets_with_confidence

        # Outer tokenizes, payload does not. Answering `parsed` would be the
        # more confident of two readings — the wrong one for a caller that
        # fails closed on uncertainty.
        _t, conf = write_targets_with_confidence("bash -c \"awk '{print $1} > x.py\"")
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
            "python environment.py",   # a NAME that starts like a prefix
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
        # already paid off once this session). `xargs` and `ssh` also carry a
        # command in their arguments, but their argument grammar is genuinely
        # different: xargs builds the command line from STDIN, and an ssh
        # payload runs on another host, where this project's paths mean nothing.
        wt = self._wt()
        assert wt("echo f.py | xargs -I{} bash -c 'echo x > {}'") == []
        assert wt("ssh host 'echo x > /remote/f.py'") == []
