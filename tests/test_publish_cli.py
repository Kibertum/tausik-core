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


def _printed_acts(out: str) -> list[str]:
    """The `git …` lines under the banner, or a loud failure — never an empty list."""
    assert "Next (" in out, out
    return [ln.strip() for ln in out.split("Next (")[1].splitlines() if ln.startswith("  git ")]


class TestTheTagActIsARefspecPushNotASecondLocalTag:
    """The finding of session #257, reproduced before it is fixed.

    The procedure builds the snapshot `--from v<version>` — a tag that already
    names the release commit on the development line — and the first cut then
    told the owner to `git tag -a v<version> <snapshot>`: git refuses, the name
    exists. The 1.8.0 precedent shows the model that works: one NAME, two
    objects (history on GitLab, snapshot on GitHub), reached by a refspec push.
    """

    def _snapshot_from_tag(self, root, head):
        _git(root, "tag", "-a", "v1.0.0", "-m", "release", "HEAD")
        code, out = _run(root, _ns(source="v1.0.0", parent=head))
        assert code == 0, out
        line = next(ln for ln in out.splitlines() if "snapshot commit:" in ln)
        return line.split()[-1], out

    def test_a_second_local_tag_of_the_same_name_is_what_git_refuses(self, repo):
        """NEGATIVE: the instruction the first cut printed cannot be executed."""
        root, head = repo
        commit, _ = self._snapshot_from_tag(root, head)
        r = _git(root, "tag", "-a", "v1.0.0", commit, "-m", "public")
        assert r.returncode != 0 and "already exists" in r.stderr, r.stderr

    def test_the_printed_acts_carry_the_tag_name_and_no_git_tag_a(self, repo):
        root, head = repo
        commit, out = self._snapshot_from_tag(root, head)
        assert f"git push github {commit}:refs/tags/v1.0.0" in out, out
        acts = _printed_acts(out)
        assert len(acts) == 2, acts
        assert not any(a.startswith("git tag") for a in acts), acts
        assert "LIGHTWEIGHT" in out, "the trade-off (no tag object) is stated where it is read"

    def test_the_printed_acts_executed_against_a_bare_remote_land_the_snapshot(
        self, repo, tmp_path
    ):
        """Run exactly what was printed; the remote ends with main and the tag on the snapshot."""
        root, head = repo
        commit, out = self._snapshot_from_tag(root, head)
        bare = tmp_path / "github.git"
        assert _git(tmp_path, "init", "--bare", str(bare)).returncode == 0
        _git(root, "remote", "add", "github", str(bare))
        acts = _printed_acts(out)
        assert len(acts) == 2, acts
        for act in acts:
            r = _git(root, *act.split()[1:])
            assert r.returncode == 0, (act, r.stderr)
        remote = dict(
            reversed(ln.split("\t")) for ln in _git(root, "ls-remote", "github").stdout.splitlines()
        )
        assert remote["refs/heads/main"] == commit
        assert remote["refs/tags/v1.0.0"] == commit
        # The local name still names the release commit on the development line.
        local_tag = _git(root, "rev-parse", "v1.0.0^{commit}").stdout.strip()
        assert local_tag == _git(root, "rev-parse", "HEAD").stdout.strip() != commit

    def test_a_source_that_is_not_a_tag_prints_a_placeholder(self, repo):
        root, head = repo
        code, out = _run(root, _ns(source="HEAD", parent=head))
        assert code == 0 and ":refs/tags/v<version>" in out

    def test_a_sha_that_one_tag_points_at_carries_that_name(self, repo):
        """`--from <sha>` copied from CI still prints the real tag, not the placeholder."""
        root, head = repo
        _git(root, "tag", "-a", "v1.0.0", "-m", "release", "HEAD")
        sha = _git(root, "rev-parse", "HEAD").stdout.strip()
        code, out = _run(root, _ns(source=sha, parent=head))
        assert code == 0 and ":refs/tags/v1.0.0" in out, out

    def test_two_tags_on_the_commit_is_an_ambiguity_not_a_guess(self, repo):
        root, head = repo
        _git(root, "tag", "v1.0.0", "HEAD")
        _git(root, "tag", "v1.0.1", "HEAD")
        code, out = _run(root, _ns(source="HEAD", parent=head))
        assert code == 0 and ":refs/tags/v<version>" in out, out
