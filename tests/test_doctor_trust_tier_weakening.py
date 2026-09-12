"""doctor names a weakening whatever tier introduced it (three states, not two).

`tausik doctor` printed "no project-scope key weakens enforcement" while
`~/.tausik/config.json` was closing tasks past the signed QG-2 receipt and
holding a blocking gate off. The sentence was literally true and therefore
misleading. The resolver could not have caught it: it measures a candidate
against the trusted tiers themselves, so a tier is never weaker than itself.

Every test here runs on a TEMPORARY user tier. The real `~/.tausik/config.json`
is neither read nor written under any outcome, and one test proves that by
watching `open` rather than by asserting it in prose.
"""

from __future__ import annotations

import builtins
import io
import json
import os
import re
from contextlib import redirect_stdout
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

import config_trust_weakening as ctw
from config_trust import Rejection
from project_cli_doctor import cmd_doctor

REAL_USER_CONFIG = os.path.abspath(os.path.join(os.path.expanduser("~"), ".tausik", "config.json"))

LONG_REASON = (
    "Misfire on a submodule layout where lib_dir differs from project_dir, "
    "recorded as dead end #126, and the note goes on at length because an "
    "operator explaining a machine-wide switch has a great deal to say about "
    "which projects it helps and which it silently costs, and every word of it "
    "belongs in the file rather than in a health check line."
)


def _write(path: str, data: dict) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


@pytest.fixture
def tiers(tmp_path, monkeypatch):
    """Point both trusted tiers at a temporary directory and hand back a writer.

    `user_config_path` honours `TAUSIK_USER_CONFIG`, so the real home directory
    becomes unreachable rather than merely unused.
    """
    user = str(tmp_path / "user.json")
    managed = str(tmp_path / "managed.json")
    monkeypatch.setenv("TAUSIK_USER_CONFIG", user)
    monkeypatch.setenv("TAUSIK_MANAGED_CONFIG", managed)

    def write(user_layer: dict | None = None, managed_layer: dict | None = None) -> tuple[str, str]:
        _write(user, user_layer or {})
        _write(managed, managed_layer or {})
        return user, managed

    return write


# --- The reader -------------------------------------------------------------


def test_a_machine_wide_weakening_in_effect_says_so_and_points_at_the_scoped_form(tiers, tmp_path):
    """Gotcha #690: the line must tell the operator that the key governs every
    project on the box and WHERE the narrower spelling goes."""
    project = str(tmp_path / "here")
    tiers({"task_done": {"auto_verify": True, "_reason": "vaflower money code"}})

    lines, ok = ctw.summary({"task_done": {"auto_verify": True}}, project)

    assert ok is None
    (line,) = lines
    assert "MACHINE-WIDE" in line
    assert 'projects["' in line and ctw.project_key(project) in line


def test_a_weakening_scoped_to_this_project_is_reported_as_such(tiers, tmp_path):
    project = str(tmp_path / "here")
    tiers({"projects": {project: {"task_done": {"auto_verify": True, "_reason": "this repo only"}}}})

    lines, ok = ctw.summary({"task_done": {"auto_verify": True}}, project)

    assert ok is None
    (line,) = lines
    assert "scoped to this project" in line
    assert "MACHINE-WIDE" not in line and 'move it under' not in line


def test_another_projects_scoped_entry_is_counted_not_applied(tiers, tmp_path):
    tiers({"projects": {str(tmp_path / "elsewhere"): {"task_done": {"auto_verify": True}}}})

    lines, ok = ctw.summary({}, str(tmp_path / "here"))

    assert lines == []
    assert ok is not None and "1 project-scoped entry for other projects, not applied here" in ok




def test_user_tier_weakening_is_named_with_its_tier_key_and_file(tiers):
    user, _ = tiers({"task_done": {"auto_verify": True, "_reason": "set for another project"}})
    (found,) = ctw.trusted_tier_weakenings()
    assert found.key == "task_done.auto_verify"
    assert found.tier == "user"
    assert (found.value, found.default) == (True, False)
    assert found.source == user
    line = found.describe()
    assert "task_done.auto_verify" in line
    assert "user tier" in line
    assert "set for another project" in line
    assert user in line


def test_gate_held_off_is_named_with_its_disabled_reason(tiers):
    tiers({"gates": {"bootstrap_drift": {"enabled": False, "_disabled_reason": "misfires here"}}})
    (found,) = ctw.trusted_tier_weakenings()
    assert found.key == "gates.bootstrap_drift.enabled"
    assert "misfires here" in found.describe()


def test_key_specific_reason_beats_the_generic_one(tiers):
    tiers({"task_done": {"auto_verify": True, "_auto_verify_reason": "exact", "_reason": "broad"}})
    (found,) = ctw.trusted_tier_weakenings()
    assert found.reason == "exact"


def test_a_weakening_with_no_reason_says_so_rather_than_printing_a_blank(tiers):
    """A decision and a mystery must not read the same."""
    tiers({"task_done": {"auto_verify": True}})
    (found,) = ctw.trusted_tier_weakenings()
    assert found.reason == ""
    assert "NO REASON RECORDED" in found.describe()


def test_managed_tier_owns_the_line_when_both_tiers_name_the_key(tiers):
    """Managed wins the merge, so it supplies the effective value; naming the
    user file would send the reader to a line whose edit changes nothing."""
    _, managed = tiers({"qg0": {"scope_hard_gate": False}}, {"qg0": {"scope_hard_gate": False}})
    (found,) = ctw.trusted_tier_weakenings()
    assert found.tier == "managed"
    assert found.source == managed


def test_long_reason_is_clipped_and_marked(tiers):
    tiers({"task_done": {"auto_verify": True, "_reason": LONG_REASON}})
    (found,) = ctw.trusted_tier_weakenings()
    assert found.reason == LONG_REASON  # the fact is kept whole
    line = found.describe()
    assert "[...]" in line
    assert LONG_REASON not in line


# --- Negative: the reader must be able to say nothing -----------------------


def test_a_tier_that_only_tightens_produces_nothing(tiers):
    """A check that speaks on every input is worth no more than one that never
    speaks. Every key here sits at or above the framework default."""
    tiers(
        {
            "task_done": {"auto_verify": False},
            "qg0": {"scope_hard_gate": True},
            "risk": {"l3_block_on_high": True},
            "gates": {"bootstrap_drift": {"enabled": True, "severity": "block"}},
        }
    )
    assert ctw.trusted_tier_weakenings() == []


def test_absent_tiers_produce_nothing(tiers, tmp_path, monkeypatch):
    monkeypatch.setenv("TAUSIK_USER_CONFIG", str(tmp_path / "nope.json"))
    monkeypatch.setenv("TAUSIK_MANAGED_CONFIG", str(tmp_path / "also-nope.json"))
    assert ctw.trusted_tier_weakenings() == []


def test_unguarded_key_is_not_judged(tiers):
    """Decision #137 leaves these outside the guarded set; a reader that
    reported them would be inventing policy the resolver does not enforce."""
    tiers({"verify_cache_ttl_seconds": 99999, "context_tier": "minimal"})
    assert ctw.trusted_tier_weakenings() == []


def test_a_gate_the_framework_does_not_ship_is_not_judged(tiers):
    """No framework default means nothing to be weaker than: a project's own
    opt-in gate shipped disabled is not a weakening of anything."""
    tiers({"gates": {"a_gate_nobody_ships": {"enabled": False}}})
    assert ctw.trusted_tier_weakenings() == []


# --- doctor -----------------------------------------------------------------


def _run_doctor(
    rejections: list[Rejection] | None = None,
    resolved: dict | None = None,
) -> str:
    """`resolved` is what `load_config_with_rejections` hands doctor — the
    EFFECTIVE config after the tiers are merged. Passing the tier layer itself
    models the ordinary case where no project key tightens it back."""
    base_cfg: dict[str, Any] = {
        "session_capacity_calls": 200,
        "session_max_minutes": 180,
        "session_warn_threshold_minutes": 150,
        "session_idle_threshold_minutes": 10,
        "verify_cache_ttl_seconds": 600,
    }
    base_cfg.update(resolved or {})

    class _Svc:
        def session_active_minutes(self) -> int:
            return 0

        def session_wall_minutes(self) -> int:
            return 0

    buf = io.StringIO()
    with (
        patch(
            "project_config.load_config_with_rejections",
            return_value=(base_cfg, rejections or []),
        ),
        redirect_stdout(buf),
    ):
        try:
            cmd_doctor(_Svc(), SimpleNamespace())
        except SystemExit:
            pass
    return buf.getvalue()


def _trust_lines(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if "Config trust tier" in ln]


def _warn_lines(out: str) -> list[str]:
    """Every WARN row, minus the trailing summary line that also carries the
    marker."""
    from project_cli_doctor import YELLOW

    return [
        ln for ln in out.splitlines() if ln.strip().startswith(YELLOW) and "warning(s)" not in ln
    ]


def _reported_warnings(out: str) -> int:
    """The warning count doctor puts in its verdict line, in EITHER form.

    doctor has two spellings — `OK with N warning(s)` and, once anything failed,
    `N FAIL, M WARN`. Reading only the first made every caller silently depend on
    nothing else in the environment having failed: in a bare checkout the missing
    database is a real FAIL, the verdict switches to the second spelling, and
    this returned 0 against three printed warnings
    (four-tests-fail-in-a-bare-checkout).
    """
    found = re.search(r"OK with (\d+) warning\(s\)", out) or re.search(r"(\d+) WARN", out)
    return int(found.group(1)) if found else 0


def _fail_lines(out: str) -> list[str]:
    """Every FAIL row, minus the trailing summary line that also carries RED."""
    from project_cli_doctor import RED

    return [ln for ln in out.splitlines() if ln.strip().startswith(RED) and "fix above" not in ln]


def _reported_failures(out: str) -> int:
    """The failure count doctor puts in its verdict line, in either form."""
    found = re.search(r"(\d+) FAIL,", out)
    return int(found.group(1)) if found else 0


def test_doctor_names_a_weakening_the_user_tier_introduced(tiers):
    """AC1/AC5: the measurement that used to require human eyes on
    `~/.tausik/config.json`, repeated here on a temporary one."""
    weak = {"task_done": {"auto_verify": True, "_reason": "set for another project"}}
    user, _ = tiers(weak)
    (line,) = _trust_lines(_run_doctor(resolved=weak))
    assert "task_done.auto_verify" in line
    assert "user tier" in line
    assert "set for another project" in line
    assert user in line


def test_doctor_calls_it_a_warning_and_not_a_failure(tiers):
    """AC3: a trusted tier is the machine owner's word. doctor owes visibility,
    not a verdict.

    The last two assertions used to be a single `"warning(s)" in out` — a read of
    doctor's SUMMARY line, which any unrelated check can flip. In a bare checkout
    it did: with no database, `Project DB — not found` is a genuine FAIL, the
    summary turned into `1 FAIL, 3 WARN`, and this test went red over a finding
    that is not its subject (four-tests-fail-in-a-bare-checkout).

    What it owes is narrower and does not depend on the environment: this row is
    carried as a warning, and it contributes NOTHING to the failure verdict.
    Stated as — the row is yellow, it is not among the failures, and doctor's
    failure count is exactly the failures it printed, so nothing yellow was
    counted as red behind the display.
    """
    from project_cli_doctor import RED, YELLOW

    weak = {"task_done": {"auto_verify": True}}
    tiers(weak)
    out = _run_doctor(resolved=weak)
    (line,) = _trust_lines(out)
    assert line.strip().startswith(YELLOW)
    assert RED not in line
    failures = _fail_lines(out)
    assert line not in failures
    assert _reported_failures(out) == len(failures)


def test_the_warning_counter_matches_the_warnings_actually_printed(tiers):
    """A printed WARN that the tally forgets makes `doctor` exit "All clean"
    with a warning on screen — and the exit line is what a CI run reads. Tying
    the count to the rows rather than to a constant keeps the two from drifting
    when an unrelated check also warns."""
    weak = {"task_done": {"auto_verify": True}}
    tiers(weak)
    out = _run_doctor(resolved=weak)
    assert len(_trust_lines(out)) == 1
    assert _reported_warnings(out) == len(_warn_lines(out))


def test_doctor_stays_silent_when_nothing_is_weakened(tiers):
    """AC6: a line that appears on every configuration reports nothing at all."""
    strict = {"task_done": {"auto_verify": False}}
    tiers(strict)
    (line,) = _trust_lines(_run_doctor(resolved=strict))
    assert "no key weakens enforcement" in line
    assert "IN EFFECT" not in line
    assert "tightened back" not in line


def test_the_project_rejection_message_is_unchanged(tiers):
    """AC2: the second state was always reported correctly. Its wording is kept
    verbatim, and it survives alongside the third rather than replacing it."""
    weak = {"task_done": {"auto_verify": True}}
    tiers(weak)
    rejection = Rejection(
        key="qg0.scope_hard_gate",
        rejected=False,
        applied=True,
        reason="project scope may only tighten scope hard gate",
    )
    lines = _trust_lines(_run_doctor([rejection], resolved=weak))
    assert len(lines) == 2
    assert rejection.describe() in lines[0]
    assert "task_done.auto_verify" in lines[1]


def test_the_three_states_never_collapse_into_each_other(tiers):
    """AC2 as one measurement: (a) clean, (b) rejected, (c) in effect are three
    distinct outputs. Collapsing (c) into (a) is the defect this task repairs."""
    strict = {"task_done": {"auto_verify": False}}
    weak = {"task_done": {"auto_verify": True}}
    tiers(strict)
    clean = _trust_lines(_run_doctor(resolved=strict))
    rejected = _trust_lines(
        _run_doctor(
            [Rejection("qg0.scope_hard_gate", False, True, "may only tighten")], resolved=strict
        )
    )
    tiers(weak)
    in_effect = _trust_lines(_run_doctor(resolved=weak))
    assert len({str(clean), str(rejected), str(in_effect)}) == 3
    assert "IN EFFECT" in in_effect[0]
    assert "IN EFFECT" not in clean[0]
    assert "IN EFFECT" not in rejected[0]


def test_a_weakening_the_project_tightens_back_is_not_a_warning(tiers):
    """The mirror of the original defect. This repository's own
    `.tausik/config.json` restores `auto_verify=false` and re-enables
    `bootstrap_drift`, so warning here would be literally true and misread the
    other way round — and a health check that cries wolf teaches the reader to
    skip the line that one day matters."""
    tiers({"task_done": {"auto_verify": True}})
    warnings, ok = ctw.summary({"task_done": {"auto_verify": False}})
    assert warnings == []
    assert ok is not None
    assert "task_done.auto_verify" in ok
    assert "tightened back" in ok


def test_doctor_prints_the_tightened_back_key_inside_the_ok_line(tiers):
    """Silence would lose the fact that the machine's tier is set that way at
    all — the next project on this machine inherits it with nothing to tighten
    it back."""
    tiers({"task_done": {"auto_verify": True}})
    (line,) = _trust_lines(_run_doctor(resolved={"task_done": {"auto_verify": False}}))
    assert "no key weakens enforcement" in line
    assert "task_done.auto_verify" in line
    assert "tightened back" in line
    assert "IN EFFECT" not in line


def test_in_effect_is_decided_by_the_resolved_config_not_by_the_tier(tiers):
    tiers({"qg0": {"scope_hard_gate": False}})
    (weak,) = ctw.trusted_tier_weakenings(effective={"qg0": {"scope_hard_gate": False}})
    (held,) = ctw.trusted_tier_weakenings(effective={"qg0": {"scope_hard_gate": True}})
    assert weak.in_effect is True
    assert held.in_effect is False
    assert "NOT in effect here" in held.describe()


# --- The real config is out of reach ----------------------------------------


def test_the_real_user_config_is_never_opened(tiers):
    """AC5, watched rather than asserted in prose: the keys in the operator's
    real tier were set for another project, and a test that read or wrote them
    would be handling somebody else's recorded decision."""
    weak = {"task_done": {"auto_verify": True}}
    tiers(weak)
    opened: list[str] = []
    real_open = builtins.open

    def spy(file, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            opened.append(os.path.abspath(os.fspath(file)))
        except TypeError:
            pass  # a file descriptor, not a path
        return real_open(file, *args, **kwargs)

    with patch.object(builtins, "open", spy):
        ctw.trusted_tier_weakenings()
        _run_doctor(resolved=weak)

    assert REAL_USER_CONFIG not in opened
