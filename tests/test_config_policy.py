"""The committed project policy — `tausik/policy.json`.

WHAT THIS FILE IS FOR, stated plainly because the previous attempt failed on
exactly this point: closing
`a-foreign-projects-config-weakens-qg2-in-our-own-repo` earned the remark
*"tier=high requires test-ref evidence — none found"*, and the remark was fair.
The strictness of this repository had been restored by editing a gitignored
file. Nothing asserted it, so nothing noticed that a fresh clone did not get it.

These tests assert the OUTCOME — this repository resolves `auto_verify` to False
and `bootstrap_drift.enabled` to True — rather than the existence of a file, and
they assert it against a hostile user tier, because a user tier that already
agrees proves nothing.

Every test here runs on a synthetic user/managed tier. The real
`~/.tausik/config.json` on this machine sets `task_done.auto_verify: true` for an
unrelated project, so a test that read it would be measuring the developer's home
directory. `TAUSIK_USER_CONFIG` is pointed at a temp file AND `HOME`/`USERPROFILE`
are redirected, so the real file is unreachable on every path, including the
fallback that runs when the env override is absent.
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

import config_policy
import config_trust as ct
from project_config import load_config_with_rejections

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY_FILE = os.path.join(REPO_ROOT, "tausik", "policy.json")


@pytest.fixture
def sealed_home(tmp_path, monkeypatch):
    """Cut every route to the real home directory, then hand back a writer.

    Returns a callable that installs a user tier; call it with the content the
    test wants the operator's machine to be pretending to have.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv(ct.MANAGED_CONFIG_ENV, raising=False)
    monkeypatch.delenv(config_policy.POLICY_ENV, raising=False)

    def install(user_tier: dict, managed: dict | None = None):
        path = tmp_path / "user_config.json"
        path.write_text(json.dumps(user_tier), encoding="utf-8")
        monkeypatch.setenv(ct.USER_CONFIG_ENV, str(path))
        if managed is not None:
            mpath = tmp_path / "managed_config.json"
            mpath.write_text(json.dumps(managed), encoding="utf-8")
            monkeypatch.setenv(ct.MANAGED_CONFIG_ENV, str(mpath))
        return path

    install({})
    return install


def _effective(tausik_dir: str) -> dict:
    return load_config_with_rejections(tausik_dir)[0]


def _auto_verify(cfg: dict):
    return cfg.get("task_done", {}).get("auto_verify")


def _bootstrap_drift(cfg: dict):
    return cfg.get("gates", {}).get("bootstrap_drift", {}).get("enabled")


# --- AC5: this repository is strict, whatever the user tier says -------------


HOSTILE_TIERS = [
    pytest.param({}, id="silent"),
    pytest.param({"task_done": {"auto_verify": True}}, id="auto_verify_on"),
    pytest.param({"gates": {"bootstrap_drift": {"enabled": False}}}, id="drift_off"),
    pytest.param(
        {
            "task_done": {"auto_verify": True},
            "gates": {"bootstrap_drift": {"enabled": False}},
        },
        id="both_relaxed",
    ),
]


@pytest.mark.parametrize("user_tier", HOSTILE_TIERS)
def test_this_repository_stays_strict_whatever_the_user_tier_says(sealed_home, user_tier):
    """The load-bearing assertion. `auto_verify` bypasses the signed receipt and
    `bootstrap_drift` is what notices a source edit that never reached the copy
    that runs; this repository requires both, and requires them from a file a
    clone receives."""
    sealed_home(user_tier)
    cfg = _effective(os.path.join(REPO_ROOT, ".tausik"))
    assert _auto_verify(cfg) is False
    assert _bootstrap_drift(cfg) is True


def test_the_managed_tier_cannot_relax_them_either(sealed_home):
    """The managed tier outranks the user tier, and still loses on a guarded key
    to a project tightening — otherwise the strictness would hold only against
    the weaker of the two trusted layers."""
    sealed_home(
        {},
        managed={
            "task_done": {"auto_verify": True},
            "gates": {"bootstrap_drift": {"enabled": False}},
        },
    )
    cfg = _effective(os.path.join(REPO_ROOT, ".tausik"))
    assert _auto_verify(cfg) is False
    assert _bootstrap_drift(cfg) is True


def test_the_policy_is_tracked_by_git(sealed_home):
    """The whole point, in the one form the effective-value tests cannot express:
    a strictness carrier that git ignores does not exist for anybody else.
    `.tausik/config.json` fails this check by construction — `.gitignore` ignores
    the directory — which is why the tightenings had to move out of it."""
    out = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "tausik/policy.json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert out.returncode == 0, "tausik/policy.json is not tracked: " + out.stderr
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "tausik/policy.json"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    assert ignored.returncode != 0, "tausik/policy.json is gitignored"


def test_a_fresh_copy_with_no_local_config_is_still_strict(sealed_home, tmp_path):
    """A clone has `tausik/policy.json` and NO `.tausik/` at all. Before this
    change the same measurement returned True/False — the tightenings existed
    only in the working copy they were typed in."""
    sealed_home({"task_done": {"auto_verify": True}})
    fresh = tmp_path / "clone"
    (fresh / "tausik").mkdir(parents=True)
    (fresh / "tausik" / "policy.json").write_text(
        open(POLICY_FILE, encoding="utf-8").read(), encoding="utf-8"
    )
    cfg = _effective(str(fresh / ".tausik"))
    assert not os.path.isdir(fresh / ".tausik")
    assert _auto_verify(cfg) is False
    assert _bootstrap_drift(cfg) is True


# --- The policy is the UNTRUSTED project tier, not a new authority ----------


def test_policy_may_not_weaken_a_guarded_key(sealed_home, tmp_path):
    """Committing a tightening buys reach, not power: a hostile clone that edits
    the committed file is judged by the same guards as one that edits the local
    one."""
    sealed_home({})
    hostile = tmp_path / "hostile.json"
    hostile.write_text(json.dumps({"qg0": {"scope_hard_gate": False}}), encoding="utf-8")
    os.environ[config_policy.POLICY_ENV] = str(hostile)
    try:
        cfg, rejections = load_config_with_rejections(str(tmp_path / ".tausik"))
    finally:
        del os.environ[config_policy.POLICY_ENV]
    assert cfg["qg0"]["scope_hard_gate"] is True
    assert [r.key for r in rejections] == ["qg0.scope_hard_gate"]


def test_a_local_config_cannot_quietly_undo_a_committed_tightening(sealed_home, tmp_path):
    """Inside the tier the stricter value wins. A gitignored file silently
    relaxing a committed rule is the defect this module was opened to close;
    re-admitting it one layer down would be the same defect with a shorter
    reach."""
    sealed_home({})
    proj = tmp_path / "proj"
    (proj / "tausik").mkdir(parents=True)
    (proj / "tausik" / "policy.json").write_text(
        json.dumps({"gates": {"mypy": {"enabled": True}}}), encoding="utf-8"
    )
    (proj / ".tausik").mkdir()
    (proj / ".tausik" / "config.json").write_text(
        json.dumps({"gates": {"mypy": {"enabled": False}}}), encoding="utf-8"
    )
    cfg = _effective(str(proj / ".tausik"))
    assert cfg["gates"]["mypy"]["enabled"] is True


def test_the_changelog_switch_is_one_of_the_keys_the_local_file_cannot_undo(sealed_home, tmp_path):
    """NEGATIVE SCENARIO, found by external review #38 and reproduced.

    This repository commits `task_done.changelog_gate.enabled: true` in
    tausik/policy.json (de9e027). The switch was not a guarded key, so a
    gitignored `.tausik/config.json` saying `false` composed over it and won —
    the exact silent undo the tier composition exists to refuse, on a
    severity=block gate. The sibling `files` list is not a switch and stays
    the local file's.
    """
    sealed_home({})
    proj = tmp_path / "proj"
    (proj / "tausik").mkdir(parents=True)
    (proj / "tausik" / "policy.json").write_text(
        json.dumps({"task_done": {"changelog_gate": {"enabled": True}}}), encoding="utf-8"
    )
    (proj / ".tausik").mkdir()
    (proj / ".tausik" / "config.json").write_text(
        json.dumps({"task_done": {"changelog_gate": {"enabled": False, "files": ["ONLY.md"]}}}),
        encoding="utf-8",
    )
    cfg = _effective(str(proj / ".tausik"))
    assert cfg["task_done"]["changelog_gate"]["enabled"] is True
    assert cfg["task_done"]["changelog_gate"]["files"] == ["ONLY.md"]


def test_the_local_config_still_wins_on_an_ordinary_key(sealed_home, tmp_path):
    """Only GUARDED keys get the stricter-wins treatment. Bootstrap metadata and
    machine paths belong to the machine, and a committed policy has no business
    overriding them."""
    sealed_home({})
    proj = tmp_path / "proj"
    (proj / "tausik").mkdir(parents=True)
    (proj / "tausik" / "policy.json").write_text(
        json.dumps({"context_tier": "minimal"}), encoding="utf-8"
    )
    (proj / ".tausik").mkdir()
    (proj / ".tausik" / "config.json").write_text(
        json.dumps({"context_tier": "standard"}), encoding="utf-8"
    )
    assert _effective(str(proj / ".tausik"))["context_tier"] == "standard"


# --- AC3: a project without the file is untouched ---------------------------


def test_a_project_with_no_policy_resolves_exactly_as_before(sealed_home, tmp_path):
    """`tausik init` writes no `tausik/policy.json`, and must not have to. An
    absent policy is not an error and not a bypass — the trusted tiers and the
    framework defaults decide alone, which is the pre-existing behaviour."""
    sealed_home({"task_done": {"auto_verify": True}})
    proj = tmp_path / "bare"
    (proj / ".tausik").mkdir(parents=True)
    (proj / ".tausik" / "config.json").write_text(json.dumps({}), encoding="utf-8")
    assert config_policy.load_policy(str(proj / ".tausik")) == {}
    assert _auto_verify(_effective(str(proj / ".tausik"))) is True


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("{not json", id="malformed"),
        pytest.param('["a", "list"]', id="wrong_root_type"),
    ],
)
def test_a_broken_policy_degrades_to_empty_rather_than_crashing(tmp_path, content, monkeypatch):
    """A config file the loader cannot read must not take down every command that
    reads config (convention #226). It degrades toward LESS project influence,
    never toward more."""
    monkeypatch.delenv(config_policy.POLICY_ENV, raising=False)
    proj = tmp_path / "proj"
    (proj / "tausik").mkdir(parents=True)
    (proj / "tausik" / "policy.json").write_text(content, encoding="utf-8")
    (proj / ".tausik").mkdir()
    assert config_policy.load_policy(str(proj / ".tausik")) == {}


def test_an_oversized_policy_is_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv(config_policy.POLICY_ENV, raising=False)
    proj = tmp_path / "proj"
    (proj / "tausik").mkdir(parents=True)
    (proj / "tausik" / "policy.json").write_text(
        '{"pad": "' + "x" * (config_policy.MAX_POLICY_BYTES + 10) + '"}', encoding="utf-8"
    )
    (proj / ".tausik").mkdir()
    assert config_policy.load_policy(str(proj / ".tausik")) == {}


def test_the_policy_is_looked_up_beside_the_handed_project_not_the_cwd(tmp_path, monkeypatch):
    """`policy_path` is derived from the caller's `.tausik/` handle, so a service
    speaking for one project never adopts an ancestor's policy — the ancestor-
    adoption failure mode the walk-up locator in `gate_filesize` had to guard
    against does not exist here."""
    monkeypatch.delenv(config_policy.POLICY_ENV, raising=False)
    assert config_policy.policy_path(str(tmp_path / "proj" / ".tausik")) == os.path.join(
        str(tmp_path / "proj"), "tausik", "policy.json"
    )


def test_writers_still_read_the_local_file_alone(sealed_home, tmp_path):
    """`save_config` persists whatever it is handed. If `load_project_config`
    composed the policy in, the first `gates enable` would copy the committed
    policy into the generated file and the two would start drifting."""
    from project_config import load_project_config

    sealed_home({})
    proj = tmp_path / "proj"
    (proj / "tausik").mkdir(parents=True)
    (proj / "tausik" / "policy.json").write_text(
        json.dumps({"task_done": {"auto_verify": False}}), encoding="utf-8"
    )
    (proj / ".tausik").mkdir()
    (proj / ".tausik" / "config.json").write_text(
        json.dumps({"context_tier": "standard"}), encoding="utf-8"
    )
    assert load_project_config(str(proj / ".tausik")) == {"context_tier": "standard"}
