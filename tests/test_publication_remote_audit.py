"""The post-publication audit reads the exact unauthenticated remote ref."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.join(_ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import publication_remote_audit as remote_audit  # noqa: E402
import publication_snapshot as snapshot  # noqa: E402
from publication_scope import PublicationError  # noqa: E402

CROSSCUTTING_SCOPE = [
    "scripts/publication_remote_audit.py",
    "scripts/publication_snapshot.py",
]


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


@pytest.fixture
def repositories(tmp_path):
    source = tmp_path / "source"
    remote = tmp_path / "public.git"
    source.mkdir()
    assert _git(source, "init", "-b", "main").returncode == 0
    _git(source, "config", "user.email", "test@example.invalid")
    _git(source, "config", "user.name", "Test")
    (source / "README.md").write_text("public\n", encoding="utf-8")
    (source / "tausik" / "tasks").mkdir(parents=True)
    (source / "tausik" / "tasks" / "internal.md").write_text("internal\n", encoding="utf-8")
    assert _git(source, "add", "-A").returncode == 0
    assert _git(source, "commit", "-m", "development").returncode == 0
    assert _git(tmp_path, "init", "--bare", str(remote)).returncode == 0
    return source, remote


def test_exact_clean_remote_ref_passes(repositories):
    source, remote = repositories
    candidate = snapshot.build_recovery_snapshot_commit(str(source), "recovery")
    assert _git(source, "push", str(remote), f"{candidate}:refs/heads/main").returncode == 0
    ok, why, observed = remote_audit.audit_remote_ref(
        str(source), str(remote), "refs/heads/main", "HEAD"
    )
    assert ok, why
    assert observed == candidate


@pytest.mark.parametrize("shape", ["whole-tree", "filtered-child"])
def test_development_tree_or_lineage_is_refused(repositories, shape):
    source, remote = repositories
    if shape == "whole-tree":
        candidate = _git(source, "rev-parse", "HEAD").stdout.strip()
    else:
        tree = snapshot.snapshot_tree(str(source), "HEAD")
        candidate = _git(
            source, "commit-tree", tree, "-p", "HEAD", "-m", "laundered"
        ).stdout.strip()
    assert _git(source, "push", str(remote), f"{candidate}:refs/heads/main").returncode == 0
    ok, why, observed = remote_audit.audit_remote_ref(
        str(source), str(remote), "refs/heads/main", "HEAD"
    )
    assert not ok
    assert observed == candidate
    assert "tree differs" in why or "excluded history" in why


def test_missing_ref_is_uncertainty_not_a_green_result(repositories):
    source, remote = repositories
    with pytest.raises(PublicationError, match="cannot resolve exact remote ref"):
        remote_audit.audit_remote_ref(str(source), str(remote), "refs/heads/missing", "HEAD")
