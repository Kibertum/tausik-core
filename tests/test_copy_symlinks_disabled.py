"""v1.3.4 (med-batch-1-hooks #3): regression for symlinks=False on copytree.

A hostile vendor skill repo or stack repo could ship a symlink with an
absolute target (e.g. /etc/passwd, ~/.aws/credentials). With
shutil.copytree's default symlinks=False, the symlink IS followed and the
target's CONTENT is materialized at the destination — i.e., the bytes get
copied as a plain file. We want exactly that behavior: the destination
file should never be a symlink, and reading it should give the target's
content (not break the bootstrap).

The previous default (symlinks parameter unspecified == False) was
already correct for shutil.copytree, but the call sites lacked an
explicit `symlinks=False` flag, which makes audit harder and risks
regression if anyone "fixes" it to symlinks=True for "fidelity".

These tests pin the explicit flag and verify the resulting tree contains
no symlinks.

Skipped on Windows when the test process can't create symlinks (default
non-admin user — `os.symlink` raises OSError). Linux/macOS always run.
"""

from __future__ import annotations

import os
import shutil
import sys

import pytest

_BOOTSTRAP_DIR = os.path.join(os.path.dirname(__file__), "..", "bootstrap")
if _BOOTSTRAP_DIR not in sys.path:
    sys.path.insert(0, _BOOTSTRAP_DIR)

_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


def _can_make_symlinks(tmp_path) -> bool:
    """Return True iff os.symlink works in this process for the target dir."""
    target = tmp_path / "_canary_target.txt"
    target.write_text("ok")
    link = tmp_path / "_canary_link"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        return False
    finally:
        try:
            link.unlink()
        except OSError:
            pass
        try:
            target.unlink()
        except OSError:
            pass
    return True


@pytest.fixture
def hostile_repo(tmp_path):
    """Create a fake repo with one regular file + one symlink to an outside file."""
    if not _can_make_symlinks(tmp_path):
        pytest.skip("Process cannot create symlinks (non-admin Windows?)")

    repo = tmp_path / "vendor-repo" / "myskill"
    repo.mkdir(parents=True)
    # Regular file inside the repo
    (repo / "SKILL.md").write_text("# myskill\n")
    # The "outside" file the symlink points to (simulates ~/.aws/credentials)
    secret = tmp_path / "outside_secret.txt"
    secret.write_text("AWS_KEY=hunter2")
    # Symlink with an absolute target outside the repo tree
    os.symlink(secret, repo / "leaked.txt")
    return repo, secret


def test_bootstrap_copy_dir_no_symlinks_in_dst(hostile_repo, tmp_path):
    """copy_dir(src=hostile_repo, dst=...) must materialize content, not link."""
    from bootstrap_copy import copy_dir

    repo, _secret = hostile_repo
    dst = tmp_path / "claude_copy" / "myskill"
    copy_dir(str(repo), str(dst))

    # Walk dst and assert no entry is a symlink
    for root, _dirs, files in os.walk(str(dst)):
        for name in files:
            p = os.path.join(root, name)
            assert not os.path.islink(p), f"unexpected symlink at {p}"

    # leaked.txt at dst should be a plain file with secret CONTENT
    # (this is the standard copytree behavior: follow + materialize)
    out = dst / "leaked.txt"
    assert out.exists()
    assert not out.is_symlink()
    assert out.read_text() == "AWS_KEY=hunter2"


def test_skill_manager_copy_skill_no_symlinks_in_dst(hostile_repo, tmp_path):
    """skill_manager.copy_skill must also call copytree with symlinks=False."""
    from skill_manager import copy_skill

    repo, _secret = hostile_repo
    skills_dst = tmp_path / "skills"
    skills_dst.mkdir()
    # repo_dir is parent containing the skill subdir; skill_info points to it
    out_dir = copy_skill(
        repo_dir=str(repo.parent),
        skill_info={"path": "myskill/"},
        skill_name="myskill",
        skills_dst=str(skills_dst),
    )
    assert out_dir is not None
    for root, _dirs, files in os.walk(out_dir):
        for name in files:
            p = os.path.join(root, name)
            assert not os.path.islink(p), f"unexpected symlink at {p}"


def test_service_skills_copytree_no_symlinks_in_dst(hostile_repo, tmp_path):
    """service_skills.skill_install code path also passes symlinks=False.

    Smoke-test the call directly on shutil.copytree with the same kwargs
    we use in service_skills (no need to spin up the full ProjectService).
    """
    repo, _secret = hostile_repo
    dst = tmp_path / "service_skills_copy"
    shutil.copytree(str(repo), str(dst), symlinks=False)
    for root, _dirs, files in os.walk(str(dst)):
        for name in files:
            p = os.path.join(root, name)
            assert not os.path.islink(p)
