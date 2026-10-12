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
import project_parser_publish as parser_publish  # noqa: E402
import publication_snapshot as snap  # noqa: E402
import ci_lane_status  # noqa: E402

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
    _git(root, "remote", "add", "github", "https://github.com/o/r.git")
    (root / "README.md").write_text("# p\n", encoding="utf-8")
    (root / "tausik" / "tasks").mkdir(parents=True)
    (root / "tausik" / "tasks" / "t.md").write_text("t\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "development root")
    head = snap.build_recovery_snapshot_commit(str(root), "public root")
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

    def test_a_development_parent_is_refused_even_for_a_dry_run(self, repo):
        root, _ = repo
        code, out = _run(root, _ns(parent="HEAD", dry_run=True))
        assert code == 1
        assert "unsafe public parent" in out and "development history" in out

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

    @pytest.mark.parametrize("flag,value", [("--timeout", "0"), ("--poll-interval", "-1")])
    def test_ci_wait_controls_must_be_positive(self, flag, value):
        parser = argparse.ArgumentParser()
        parser_publish.add_publish(parser.add_subparsers(dest="command"))
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "publish",
                    "ci-check",
                    "--snapshot",
                    "a" * 40,
                    "--tag",
                    "v1.0.0",
                    flag,
                    value,
                ]
            )

    def test_ci_check_has_no_caller_selectable_repository(self):
        parser = argparse.ArgumentParser()
        parser_publish.add_publish(parser.add_subparsers(dest="command"))
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "publish",
                    "ci-check",
                    "--snapshot",
                    "a" * 40,
                    "--tag",
                    "v1.0.0",
                    "--repo",
                    "attacker/fork",
                ]
            )


class TestTheHappyPathReportsAndWritesNoRef:
    def test_dry_run_reports_and_writes_no_commit(self, repo):
        root, head = repo
        before = _git(root, "rev-list", "--all", "--count").stdout.strip()
        code, out = _run(root, _ns(parent=head, dry_run=True))
        assert code == 0
        assert "published: 1 file(s)" in out and "excluded:  1 file(s)" in out
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
        assert "git push github" in out and "publish ci-check" in out
        assert ":refs/tags/" not in out
        assert "--force" in out and "never --force" in out
        assert _git(root, "rev-parse", "HEAD").stdout.strip() != commit, "no ref moved"
        code2, out2 = _run(root, _ns(publish_cmd="verify", snapshot=commit, source="HEAD"))
        assert code2 == 0 and out2.startswith("OK")

    def test_recovery_builds_a_verified_root_but_prints_no_push_act(self, repo):
        root, _ = repo
        code, out = _run(root, _ns(publish_cmd="recovery", message="recovery"))
        assert code == 0, out
        line = next(ln for ln in out.splitlines() if "recovery commit:" in ln)
        commit = line.split()[-1]
        assert _git(root, "rev-list", "--parents", "-n", "1", commit).stdout.split() == [commit]
        assert "OWNER APPROVAL REQUIRED" in out
        assert "git push" not in out

    def test_verify_rejects_a_filtered_tip_over_development_history(self, repo):
        root, _ = repo
        tree = snap.snapshot_tree(str(root), "HEAD")
        candidate = _git(root, "commit-tree", tree, "-p", "HEAD", "-m", "laundered").stdout.strip()
        code, out = _run(root, _ns(publish_cmd="verify", snapshot=candidate, source="HEAD"))
        assert code == 1 and "shares development history" in out

    def test_remote_audit_reads_the_exact_ref_and_reports_its_commit(self, repo, tmp_path):
        root, _ = repo
        head = snap.build_recovery_snapshot_commit(str(root), "current recovery")
        remote = tmp_path / "public.git"
        assert _git(tmp_path, "init", "--bare", str(remote)).returncode == 0
        assert _git(root, "push", str(remote), f"{head}:refs/heads/main").returncode == 0
        code, out = _run(
            root,
            _ns(
                publish_cmd="remote-audit",
                remote=str(remote),
                ref="refs/heads/main",
                source="HEAD",
            ),
        )
        assert code == 0, out
        assert head in out and "refs/heads/main" in out

    def test_remote_audit_refuses_a_missing_ref_without_calling_it_clean(self, repo, tmp_path):
        root, _ = repo
        remote = tmp_path / "public.git"
        assert _git(tmp_path, "init", "--bare", str(remote)).returncode == 0
        code, out = _run(
            root,
            _ns(
                publish_cmd="remote-audit",
                remote=str(remote),
                ref="refs/heads/missing",
                source="HEAD",
            ),
        )
        assert code == 1 and out.startswith("REFUSED:")
        assert "cannot resolve exact remote ref" in out


def _printed_acts(out: str) -> list[str]:
    """The `git …` lines under the banner, or a loud failure — never an empty list."""
    assert "Next (" in out, out
    return [ln.strip() for ln in out.split("Next (")[1].splitlines() if ln.startswith("  git ")]


class TestTagIsUnreachableUntilExactCandidateCIIsGreen:
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

    def _ci_check(self, root, commit, monkeypatch, *, green=True):
        monkeypatch.setattr(
            ci_lane_status,
            "wait_for_exact",
            lambda slug, sha, timeout, poll_interval: (
                green,
                "candidate is GREEN" if green else "candidate is FAILURE",
            ),
        )
        return _run(
            root,
            _ns(
                publish_cmd="ci-check",
                snapshot=commit,
                source="v1.0.0",
                tag="v1.0.0",
                timeout=10,
                poll_interval=1,
            ),
        )

    def test_a_second_local_tag_of_the_same_name_is_what_git_refuses(self, repo):
        """NEGATIVE: the instruction the first cut printed cannot be executed."""
        root, head = repo
        commit, _ = self._snapshot_from_tag(root, head)
        r = _git(root, "tag", "-a", "v1.0.0", commit, "-m", "public")
        assert r.returncode != 0 and "already exists" in r.stderr, r.stderr

    def test_snapshot_prints_main_and_ci_check_but_no_tag_act(self, repo):
        root, head = repo
        commit, out = self._snapshot_from_tag(root, head)
        assert f"git push github {commit}:refs/heads/main" in out
        assert f"publish ci-check --snapshot {commit}" in out
        assert "--tag v1.0.0" in out
        assert ":refs/tags/" not in out
        acts = _printed_acts(out)
        assert len(acts) == 1, acts

    def test_only_green_exact_sha_emits_the_tag_refspec(self, repo, monkeypatch):
        root, head = repo
        commit, _ = self._snapshot_from_tag(root, head)
        code, out = self._ci_check(root, commit, monkeypatch)
        assert code == 0, out
        assert f"git push github {commit}:refs/tags/v1.0.0" in out
        assert "LIGHTWEIGHT" in out
        assert not any(a.startswith("git tag") for a in _printed_acts(out))

    def test_red_candidate_refuses_and_prints_no_tag_act(self, repo, monkeypatch):
        root, head = repo
        commit, _ = self._snapshot_from_tag(root, head)
        code, out = self._ci_check(root, commit, monkeypatch, green=False)
        assert code == 1 and "REFUSED" in out
        assert ":refs/tags/" not in out

    def test_ci_check_uses_the_named_release_remote_not_a_fork(self, repo, monkeypatch):
        root, head = repo
        commit, _ = self._snapshot_from_tag(root, head)
        _git(root, "remote", "add", "fork", "https://github.com/attacker/fork.git")
        seen = []
        monkeypatch.setattr(
            ci_lane_status,
            "wait_for_exact",
            lambda slug, sha, timeout, poll_interval: (seen.append(slug) is None, "GREEN"),
        )
        code, out = _run(
            root,
            _ns(
                publish_cmd="ci-check",
                snapshot=commit,
                source="v1.0.0",
                tag="v1.0.0",
                timeout=10,
                poll_interval=1,
            ),
        )
        assert code == 0 and "refs/tags/v1.0.0" in out
        assert seen == ["o/r"]

    def test_the_printed_acts_executed_against_a_bare_remote_land_the_snapshot(
        self, repo, tmp_path, monkeypatch
    ):
        """Run exactly what was printed; the remote ends with main and the tag on the snapshot."""
        root, head = repo
        commit, snapshot_out = self._snapshot_from_tag(root, head)
        bare = tmp_path / "github.git"
        assert _git(tmp_path, "init", "--bare", str(bare)).returncode == 0
        code, ci_out = self._ci_check(root, commit, monkeypatch)
        assert code == 0
        _git(root, "remote", "set-url", "github", str(bare))
        main_acts = _printed_acts(snapshot_out)
        assert len(main_acts) == 1
        for act in main_acts:
            r = _git(root, *act.split()[1:])
            assert r.returncode == 0, (act, r.stderr)
        tag_acts = _printed_acts(ci_out)
        assert len(tag_acts) == 1
        for act in tag_acts:
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

    def test_a_source_that_is_not_a_tag_prints_a_ci_placeholder_not_a_tag_act(self, repo):
        root, head = repo
        code, out = _run(root, _ns(source="HEAD", parent=head))
        assert code == 0 and "--tag v<version>" in out
        assert ":refs/tags/" not in out

    def test_a_sha_that_one_tag_points_at_carries_that_name(self, repo):
        """`--from <sha>` copied from CI still prints the real tag, not the placeholder."""
        root, head = repo
        _git(root, "tag", "-a", "v1.0.0", "-m", "release", "HEAD")
        sha = _git(root, "rev-parse", "HEAD").stdout.strip()
        code, out = _run(root, _ns(source=sha, parent=head))
        assert code == 0 and "--tag v1.0.0" in out, out
        assert ":refs/tags/" not in out

    def test_two_tags_on_the_commit_is_an_ambiguity_not_a_guess(self, repo):
        root, head = repo
        _git(root, "tag", "v1.0.0", "HEAD")
        _git(root, "tag", "v1.0.1", "HEAD")
        code, out = _run(root, _ns(source="HEAD", parent=head))
        assert code == 0 and "--tag v<version>" in out, out
        assert ":refs/tags/" not in out

    def test_a_shell_active_tag_is_never_printed_as_a_command(self, repo):
        root, head = repo
        _git(root, "tag", "v1.0.0;whoami", "HEAD")
        code, out = _run(root, _ns(source="HEAD", parent=head))
        assert code == 0 and "--tag v<version>" in out
        assert ";whoami" not in out
