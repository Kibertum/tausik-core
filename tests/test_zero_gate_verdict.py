"""A run in which no gate executed is not a positive verdict (SENAR 1.4 §8.6(e)).

Measured live in session #177: `verify --task <slug> --no-tests-expected`
printed "no gate actually executed", recorded the run with
`no_tests_declared=1`, exited 0 and minted a handle that closed the task. The
label was honest; the verdict was not. §8.6(e) is a SHALL on every
configuration and the standard says expressly that it is not weakened on any of
them.

Every test here carries both ends. A verdict property can always be satisfied
by refusing everything, and refusing everything is what an earlier version of
this branch did (`verify-no-test-mapped-dead-end`) — a documentation or config
task honestly maps to no test and must stay closable. So the exemption is
pinned as hard as the refusal.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from conftest import VERIFICATION_RUNS_DDL  # noqa: E402
from verify_handle_check import check_handle  # noqa: E402
from verify_zero_gate import (  # noqa: E402
    ACK_FLAG,
    APPLICABLE_DID_NOT_RUN,
    EXECUTED,
    NONE_APPLICABLE,
    executed_gates,
    rests_on_a_declaration,
    run_state,
)

#: This module walks `scripts/` and `harness/` in
#: `test_only_two_call_sites_read_the_recent_lookup`, so scoped-pytest — which
#: picks tests by file NAME from relevant_files — would never select it for an
#: edit under those trees. Declaring the scope is not bookkeeping: the guard
#: that must go red when a FOURTH reader of the recent-run lookup appears is
#: precisely the one a scoped run would otherwise skip, and a check that does
#: not execute looks exactly like a check that found nothing.
CROSSCUTTING_SCOPE = ["scripts/", "harness/"]

NONCE = "a" * 32


def _ran(name="pytest", passed=True):
    return {
        "name": name,
        "passed": passed,
        "skipped": False,
        "outcome": "PASSED" if passed else "FAILED",
    }


def _not_applicable(name="hadolint"):
    return {"name": name, "passed": True, "skipped": True, "outcome": "NOT_APPLICABLE"}


def _could_not_run(name="pytest"):
    return {"name": name, "passed": False, "skipped": True, "outcome": "COULD_NOT_RUN"}


def _legacy_skip(name="pytest"):
    """A row written before `gate_outcome` existed: only the boolean."""
    return {"name": name, "passed": True, "skipped": True}


# --- the three states (AC6) -----------------------------------------------


def test_a_gate_that_ran_is_an_execution():
    assert run_state([_ran(), _not_applicable()]) == EXECUTED
    assert [r["name"] for r in executed_gates([_ran(), _not_applicable()])] == ["pytest"]


def test_nothing_applicable_is_the_legitimate_state():
    assert run_state([_not_applicable("hadolint"), _not_applicable("pytest")]) == NONE_APPLICABLE


def test_a_gate_that_applied_and_did_not_run_is_the_forbidden_state():
    assert run_state([_could_not_run()]) == APPLICABLE_DID_NOT_RUN


def test_a_legitimate_skip_does_not_launder_a_gate_that_could_not_run():
    """AC6's whole point: the two must not collapse, and the worse one wins."""
    assert run_state([_not_applicable("hadolint"), _could_not_run("pytest")]) == (
        APPLICABLE_DID_NOT_RUN
    )


def test_no_results_at_all_is_not_nothing_applicable():
    """We cannot say a gate did not apply when no gate was ever consulted."""
    assert run_state([]) == APPLICABLE_DID_NOT_RUN


def test_a_legacy_result_without_an_outcome_is_not_read_as_an_execution():
    assert run_state([_legacy_skip()]) == NONE_APPLICABLE
    assert executed_gates([_legacy_skip()]) == []


@pytest.mark.parametrize(
    "raw,expected",
    [(1, True), ("1", True), (True, True), (0, False), ("0", False), (None, False), ("", False)],
)
def test_rests_on_a_declaration_reads_the_column(raw, expected):
    assert rests_on_a_declaration({"no_tests_declared": raw}) is expected


# --- the handle: refused without the acknowledgement, accepted with it ----


@pytest.fixture
def conn(tmp_path):
    from backend_schema_gate_runs import GATE_RUNS_SQL

    c = sqlite3.connect(str(tmp_path / "t.db"))
    c.row_factory = sqlite3.Row
    c.executescript(VERIFICATION_RUNS_DDL)
    c.executescript(GATE_RUNS_SQL)
    c.commit()
    yield c
    c.close()


def _insert_run(conn, *, no_tests_declared=1, command="trigger=verify|files=a.md"):
    conn.execute(
        "INSERT INTO verification_runs "
        "(task_slug, scope, command, exit_code, summary, files_hash, ran_at, "
        " duration_ms, no_tests_declared, handle_nonce, handle_expires_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            "doc-task",
            "manual",
            command,
            0,
            "hadolint=SKIP, pytest=SKIP",
            "hash",
            "2099-01-01T00:00:00Z",
            10,
            no_tests_declared,
            NONCE,
            "2099-01-01T00:00:00Z",
        ),
    )
    conn.commit()
    return int(conn.execute("SELECT MAX(id) FROM verification_runs").fetchone()[0])


def test_a_handle_for_a_run_with_no_executed_gate_is_refused(conn, tmp_path):
    """AC5. Before this task the same handle closed the task."""
    run_id = _insert_run(conn)
    verdict = check_handle(
        conn, f"{run_id}.{NONCE}", task_slug="doc-task", project_dir=str(tmp_path)
    )
    assert verdict.ok is False
    assert "executed NO gate" in verdict.reason
    assert ACK_FLAG in verdict.reason, "a refusal without a remedy is a dead end"
    assert "§8.6(e)" in verdict.reason


def test_the_same_handle_is_accepted_once_the_closer_acknowledges(conn, tmp_path):
    """AC3. The way out must exist, or the fix is a ban on documentation work."""
    run_id = _insert_run(conn)
    verdict = check_handle(
        conn,
        f"{run_id}.{NONCE}",
        task_slug="doc-task",
        project_dir=str(tmp_path),
        zero_gate_ack=True,
    )
    assert "executed NO gate" not in (verdict.reason or "")


def test_an_ordinary_run_is_unaffected_by_the_acknowledgement_default(conn, tmp_path):
    """The other end: a run that DID execute a gate must not need the flag."""
    run_id = _insert_run(conn, no_tests_declared=0)
    verdict = check_handle(
        conn, f"{run_id}.{NONCE}", task_slug="doc-task", project_dir=str(tmp_path)
    )
    assert "executed NO gate" not in (verdict.reason or "")


# --- the second door: closing WITHOUT a handle ----------------------------


def test_the_freshness_lookup_also_refuses_a_run_that_executed_nothing(conn, monkeypatch):
    """The handle is not the only way to close.

    `has_fresh_verify_run` matches on command and files_hash, and the
    no-test-mapped branch records its row with a CLEAN command — the
    `noncacheable|` stamp is applied only after that branch has returned. So
    the run was replayable here for the whole cache TTL.
    """
    import verify_cache

    run_id = _insert_run(conn)
    monkeypatch.setattr(verify_cache, "is_cache_allowed", lambda _f: True)
    monkeypatch.setattr(verify_cache, "coverage_files", lambda f, _s: list(f))
    monkeypatch.setattr(verify_cache, "compute_files_hash", lambda _f: "hash")
    monkeypatch.setattr(
        verify_cache, "_build_cache_command", lambda *_a, **_k: "trigger=verify|files=a.md"
    )
    fresh, hit = verify_cache.has_fresh_verify_run(conn, "doc-task", ["a.md"], max_age_s=10**9)
    assert fresh is False
    assert hit is not None and int(hit["id"]) == run_id, (
        "the refusal must still name the run it rejected"
    )


def test_the_freshness_lookup_still_accepts_a_run_that_executed_something(conn, monkeypatch):
    import verify_cache

    _insert_run(conn, no_tests_declared=0)
    monkeypatch.setattr(verify_cache, "is_cache_allowed", lambda _f: True)
    monkeypatch.setattr(verify_cache, "coverage_files", lambda f, _s: list(f))
    monkeypatch.setattr(verify_cache, "compute_files_hash", lambda _f: "hash")
    monkeypatch.setattr(
        verify_cache, "_build_cache_command", lambda *_a, **_k: "trigger=verify|files=a.md"
    )
    fresh, hit = verify_cache.has_fresh_verify_run(conn, "doc-task", ["a.md"], max_age_s=10**9)
    assert fresh is True and hit is not None


# --- AC4: the fileless close is a different animal ------------------------


def test_only_the_changelog_gate_skips_on_a_fileless_close():
    """AC4, answered by measurement rather than assumed.

    `--no-file-changes` does NOT produce an empty positive verdict: the only
    gate that skips on it is `changelog`, which ships DISABLED, while
    Verify-First keeps running and takes its own third route — one that
    requires git to prove the declared scope has no uncommitted changes. That
    is a check with evidence behind it, and git's evidence at that, not the
    agent's word.
    """
    from gate_registry import GATE_REGISTRY

    specs = list(GATE_REGISTRY.values())
    skipping = [s.name for s in specs if s.skip_on_fileless_close]
    assert skipping == ["changelog"]
    assert GATE_REGISTRY["changelog"].default_config["enabled"] is False
    verify_first = next(s for s in specs if "verify" in s.name)
    assert verify_first.skip_on_fileless_close is False


# --- the command itself: the declaration cannot launder a gate that broke ---


def _handle(conn, results, *, no_tests_expected=True):
    from verify_no_test_mapped import handle_no_test_mapped

    return handle_no_test_mapped(
        conn,
        slug="doc-task",
        files=["docs/x.md"],
        results=results,
        scope="manual",
        cache_command="trigger=verify|files=docs/x.md",
        files_hash="hash",
        duration_ms=1,
        scope_desc={},
        trigger="verify",
        details=None,
        no_tests_expected=no_tests_expected,
        append_notes_fn=None,
    )


def test_nothing_applicable_plus_a_declaration_records_the_exemption(conn):
    passed, results, status = _handle(
        conn, [_not_applicable("hadolint"), _not_applicable("pytest")]
    )
    assert passed is True
    assert status == "no-tests-declared"
    row = conn.execute("SELECT no_tests_declared FROM verification_runs").fetchone()
    assert int(row[0]) == 1, "the exemption has to be countable, not just permitted"
    assert len(results) == 2, "no synthetic failure is appended to a legitimate run"


def test_a_gate_that_could_not_run_is_not_declared_away(conn):
    """AC6. `--no-tests-expected` declares that no test was EXPECTED. It cannot
    declare away a gate that was expected and then produced nothing."""
    passed, results, status = _handle(conn, [_not_applicable("hadolint"), _could_not_run("pytest")])
    assert passed is False
    assert status == "gate-could-not-run"
    assert results[-1]["severity"] == "block"
    assert "cannot be acknowledged away" in results[-1]["output"]
    assert conn.execute("SELECT COUNT(*) FROM verification_runs").fetchone()[0] == 0, (
        "a run that certifies nothing must not be written as an exemption"
    )


def test_without_the_declaration_the_branch_still_blocks(conn):
    """The pre-existing contract is untouched: no flag, no way through."""
    passed, _results, status = _handle(conn, [_not_applicable("hadolint")], no_tests_expected=False)
    assert passed is False
    assert status != "no-tests-declared"


# --- what the operator is told --------------------------------------------


def test_the_verify_note_is_not_a_verdict():
    from verify_zero_gate import verdict_note

    legitimate = verdict_note(NONE_APPLICABLE)
    assert legitimate.startswith("NOT A VERDICT")
    assert ACK_FLAG in legitimate, "the note must name the way forward"

    broken = verdict_note(APPLICABLE_DID_NOT_RUN)
    assert broken.startswith("NOT A VERDICT")
    assert ACK_FLAG not in broken, "a gate that could not run is fixed, not acknowledged"


# --- the THIRD door (review record #26, critical) -------------------------
# The zero-gate rule was wired into two of the three readers of
# `lookup_recent_for_task`. The third lives inside `run_gates_with_cache` and is
# reached by `gate_verify_first`'s auto_verify branch — precisely when the
# freshness lookup has just refused. A row with no_tests_declared=1 therefore
# satisfied Verify-First one line after being rejected, and the task closed with
# no gate executed and no acknowledgement.


def test_only_two_call_sites_read_the_recent_lookup():
    """AC3: the inventory is by the LOWER primitive, not by a convenient wrapper.

    The critical was missed because consumers were inventoried by the name
    `has_fresh_verify_run`, while the third reader calls the primitive itself.

    WHAT THIS PROVES, EXACTLY. Every module under `scripts/` and `harness/` is
    parsed and every direct call to the name is counted through the AST, so a
    caller added in `scripts/hooks/`, `scripts/providers/` or the MCP tree is a
    red test. The first version of this guard used a flat `os.listdir` over
    `scripts/` and a text regex — it saw neither subdirectory nor `harness/`,
    which is the same "inventoried the convenient level" mistake one directory
    down, and the fix review caught it. What it still does NOT prove: a call
    reached through an alias (`fn = lookup_recent_for_task; fn(...)`) or
    `getattr`. That limit is stated rather than papered over.
    """
    import ast

    callers: dict[str, int] = {}
    for root in ("scripts", "harness"):
        for dirpath, _dirs, files in os.walk(os.path.join(_ROOT, root)):
            if "__pycache__" in dirpath:
                continue
            for name in files:
                if not name.endswith(".py") or name == "verify_recent_lookup.py":
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as handle:
                    try:
                        tree = ast.parse(handle.read())
                    except SyntaxError:  # pragma: no cover - not our file to fix
                        continue
                hits = sum(
                    1
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "lookup_recent_for_task"
                )
                if hits:
                    callers[os.path.relpath(path, _ROOT).replace("\\", "/")] = hits

    assert callers == {"scripts/verify_cache.py": 1, "scripts/verify_cached_run.py": 1}, (
        f"a new reader of the recent-run lookup must decide about no_tests_declared too: {callers}"
    )


def _run_with_cache(conn, tmp_path, monkeypatch, *, zero_gate_ack=False):
    import verify_cached_run

    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.md").write_text("# x", encoding="utf-8")
    monkeypatch.setattr(verify_cached_run, "compute_files_hash", lambda _f: "hash")
    monkeypatch.setattr(verify_cached_run, "is_cache_allowed", lambda _f: True)
    monkeypatch.setattr(verify_cached_run, "_build_cache_command", lambda *_a, **_k: "cmd")
    monkeypatch.setattr(
        verify_cached_run, "describe_declared_scope", lambda *_a, **_k: {"status": "declared"}
    )
    ran = {"n": 0}

    def _fake_run_gates(*_a, **_kw):
        ran["n"] += 1
        return True, [_ran("pytest")]

    import gate_runner

    monkeypatch.setattr(gate_runner, "run_gates", _fake_run_gates)
    passed, results, status = verify_cached_run.run_gates_with_cache(
        conn,
        "doc-task",
        ["a.md"],
        trigger="verify",
        allow_handle=False,
        zero_gate_ack=zero_gate_ack,
    )
    return passed, status, ran["n"]


def test_the_cache_hit_does_not_replay_a_run_that_executed_nothing(conn, tmp_path, monkeypatch):
    """AC2 negative: this passed as a cache HIT before the fix, closing the task."""
    _insert_run(conn, command="cmd")
    _passed, status, ran = _run_with_cache(conn, tmp_path, monkeypatch)
    assert status != "hit", "an empty verdict must not be replayed as a certificate"
    assert ran == 1, "the honest answer is to run the gates, not to refuse outright"


def test_the_cache_hit_is_replayed_once_the_closer_acknowledges(conn, tmp_path, monkeypatch):
    """The other end: the acknowledgement opens this door like the other two."""
    _insert_run(conn, command="cmd")
    passed, status, ran = _run_with_cache(conn, tmp_path, monkeypatch, zero_gate_ack=True)
    assert (passed, status, ran) == (True, "hit", 0)


def test_an_ordinary_cached_run_is_still_replayed(conn, tmp_path, monkeypatch):
    """The guard must not turn every cache hit into a re-run."""
    _insert_run(conn, no_tests_declared=0, command="cmd")
    passed, status, ran = _run_with_cache(conn, tmp_path, monkeypatch)
    assert (passed, status, ran) == (True, "hit", 0)


# --- the acknowledgement must survive the layer boundary ------------------
# Mutation survivor: `zero_gate_ack=zero_gate_ack` in the auto_verify branch of
# `gate_verify_first` could be replaced by a hardcoded False and every test
# stayed green — the tests above call `run_gates_with_cache` directly and never
# cross that boundary. The auto_verify branch is reached exactly when the
# freshness lookup has just refused, so dropping the flag there restores the
# critical: refused at one door, admitted at the next.


class _Be:
    def __init__(self, conn):
        self._conn = conn
        self.notes: list[str] = []

    def task_append_notes(self, _slug, note):
        self.notes.append(note)

    def event_add(self, *_a, **_kw):
        return None


class _Svc:
    def __init__(self, conn):
        self.be = _Be(conn)


@pytest.mark.parametrize("ack", [True, False])
def test_the_auto_verify_branch_forwards_the_acknowledgement(conn, monkeypatch, tmp_path, ack):
    import gate_verify_first

    monkeypatch.setattr(
        "project_config.load_config", lambda *_a, **_k: {"task_done": {"auto_verify": True}}
    )
    monkeypatch.setattr(
        "project_config.get_gates_for_trigger",
        lambda trigger, cfg=None: (
            [{"name": "pytest", "enabled": True, "trigger": ["verify"], "command": "pytest"}]
            if trigger == "verify"
            else []
        ),
    )
    monkeypatch.setattr(gate_verify_first, "_project_dir", lambda _svc: str(tmp_path))

    seen: dict[str, object] = {}

    def _fake_run_gates_with_cache(*_a, **kw):
        seen.update(kw)
        return True, [_ran("pytest")], "miss"

    import service_verification

    monkeypatch.setattr(
        service_verification, "has_fresh_verify_run", lambda *_a, **_k: (False, None)
    )
    monkeypatch.setattr(service_verification, "run_gates_with_cache", _fake_run_gates_with_cache)

    report: dict = {"blocking_failures": []}
    gate_verify_first.enforce_verify_first(
        _Svc(conn), report, "doc-task", ["a.md"], zero_gate_ack=ack
    )
    assert seen.get("zero_gate_ack") is ack, (
        "the acknowledgement is an act of the closer and must reach every door"
    )


# --- the remedy names the act that is actually missing --------------------
# Fix review of the fix: after the zero-gate guard sets a cached hit aside, the
# gates run for real, land on the same all-skipped result, and the generic block
# says "re-run verify with --no-tests-expected" — which the closer already did.
# The missing act is on the CLOSING side.


def test_the_block_after_a_reset_names_the_closing_side_flag(conn):
    from verify_no_test_mapped import handle_no_test_mapped

    notes: list[str] = []
    passed, results, _status = handle_no_test_mapped(
        conn,
        slug="doc-task",
        files=["docs/x.md"],
        results=[_not_applicable("pytest")],
        scope="manual",
        cache_command="cmd",
        files_hash="hash",
        duration_ms=1,
        scope_desc={},
        trigger="verify",
        details=None,
        no_tests_expected=False,
        append_notes_fn=lambda _s, note: notes.append(note),
        after_zero_gate_reset=True,
    )
    assert passed is False
    blocked = results[-1]["output"]
    assert ACK_FLAG in blocked
    assert "re-run verify with --no-tests-expected" not in blocked
    assert ACK_FLAG in notes[-1]


def test_the_ordinary_block_still_gives_the_ordinary_advice(conn):
    """The other end: a scope that never declared anything must still be told
    to add a test or to declare — the new wording is for the reset case only."""
    from verify_no_test_mapped import handle_no_test_mapped

    _passed, results, _status = handle_no_test_mapped(
        conn,
        slug="doc-task",
        files=["docs/x.md"],
        results=[_not_applicable("pytest")],
        scope="manual",
        cache_command="cmd",
        files_hash="hash",
        duration_ms=1,
        scope_desc={},
        trigger="verify",
        details=None,
        no_tests_expected=False,
        append_notes_fn=None,
    )
    blocked = results[-1]["output"]
    assert "--no-tests-expected" in blocked
    assert ACK_FLAG not in blocked
