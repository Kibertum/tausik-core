"""`tausik publish` refuses cleanly and reports honestly — the layer the operator reads.

The mechanism lives in `publication_snapshot` and is tested there; this file
drives `cmd_publish` the way the CLI does (a service handle and an argparse
namespace) because the first cut crashed with a raw traceback on a typo'd
`--from` (review, session #256) — the one layer that talks to a person had no
test. Refusals here are exit codes and printed lines, never exceptions.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.join(_ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import project_cli_publish as cli  # noqa: E402
import publication_snapshot as snap  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/project_cli_publish.py", "scripts/project_parser_publish.py"]


def _git(cwd, *args) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


class _Svc:
    def __init__(self, root):
        self._t = os.path.join(str(root), ".tausik")

    def tausik_dir(self) -> str:
        return self._t


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / ".tausik").mkdir(parents=True)
    assert _git(root, "init", "-b", "main").returncode == 0
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("# p\n", encoding="utf-8")
    (root / "tausik" / "tasks").mkdir(parents=True)
    (root / "tausik" / "tasks" / "t.md").write_text("t\n", encoding="utf-8")
    (root / "TODO.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "public head")
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    (root / "README.md").write_text("# p2\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "dev")
    return root, head


def _ns(**kw) -> argparse.Namespace:
    base = {
        "publish_cmd": "snapshot",
        "source": "HEAD",
        "parent": None,
        "message": None,
        "dry_run": False,
    }
    base.update(kw)
    return argparse.Namespace(**base)


def _run(root, ns) -> tuple[int, str]:
    import io
    from contextlib import redirect_stdout

    out = io.StringIO()
    with redirect_stdout(out):
        try:
            cli.cmd_publish(_Svc(root), ns)
            code = 0
        except SystemExit as e:
            code = int(e.code or 0)
    return code, out.getvalue()


class TestRefusalsAreCleanLines:
    def test_a_typo_in_from_is_a_refusal_not_a_traceback(self, repo):
        root, head = repo
        code, out = _run(root, _ns(source="no-such-ref", parent=head, dry_run=True))
        assert code == 1
        assert out.startswith("REFUSED:"), out

    def test_a_parent_that_is_not_a_commit_is_refused_before_any_scan(self, repo, monkeypatch):
        root, _ = repo
        monkeypatch.setattr(
            snap, "leaks_in_snapshot", lambda *a, **k: pytest.fail("scan ran first")
        )
        code, out = _run(root, _ns(parent="0" * 40, dry_run=True))
        assert code == 1 and "--parent" in out and "not a commit" in out

    def test_a_typo_in_snapshot_is_a_refusal(self, repo):
        root, _ = repo
        code, out = _run(root, _ns(publish_cmd="verify", snapshot="no-such-sha", source="HEAD"))
        assert code == 1 and out.startswith("REFUSED:")

    def test_a_leak_on_the_snapshot_refuses(self, repo, monkeypatch):
        root, head = repo
        monkeypatch.setattr(
            snap,
            "leaks_in_snapshot",
            lambda *a, **k: {"internal host": ["docs/x.md"], "dev-machine path": []},
        )
        code, out = _run(root, _ns(parent=head, dry_run=True))
        assert code == 1 and "REFUSED: a leak class" in out and "docs/x.md" in out

    def test_no_subcommand_prints_usage(self, repo):
        root, _ = repo
        code, out = _run(root, _ns(publish_cmd=None))
        assert code == 2 and "Usage:" in out


class TestTheHappyPathReportsAndWritesNoRef:
    def test_dry_run_reports_and_writes_no_commit(self, repo):
        root, head = repo
        before = _git(root, "rev-list", "--all", "--count").stdout.strip()
        code, out = _run(root, _ns(parent=head, dry_run=True))
        assert code == 0
        assert "published: 1 file(s)" in out and "excluded:  2 file(s)" in out
        assert "DRY RUN" in out and "filtered tree:" in out
        assert _git(root, "rev-list", "--all", "--count").stdout.strip() == before

    def test_the_real_run_names_the_commit_and_the_owner_s_next_acts(self, repo):
        root, head = repo
        code, out = _run(root, _ns(parent=head))
        assert code == 0, out
        line = next(ln for ln in out.splitlines() if "snapshot commit:" in ln)
        commit = line.split()[-1]
        assert _git(root, "rev-parse", f"{commit}^").stdout.strip() == head
        assert "OK  snapshot tree" in out and "remains an ancestor" in out
        assert "git push github" in out and "--force" in out and "never --force" in out
        assert _git(root, "rev-parse", "HEAD").stdout.strip() != commit, "no ref moved"
        code2, out2 = _run(root, _ns(publish_cmd="verify", snapshot=commit, source="HEAD"))
        assert code2 == 0 and out2.startswith("OK")
