"""gate-registry-single-source — one declaration per built-in gate.

Declaring a gate used to mean landing in four unconnected places: metadata in
`default_gates`, dispatch in a chain of `if name == ...` in `gate_runner`,
"is it built-in?" inferred from `command is None` in `gate_command_policy`, and
— for the two QG-2 gates that run after the scoped pipeline — a hardcoded call
in `service_gates`. The last of those was invisible everywhere else, and the
consequence was concrete: `gate_changelog` and `gate_verify_first` were not
listed by `gates status`, could not be toggled, and wrote no `gate_runs` row,
so nothing downstream could prove the QG-2 gate had actually run.

What these tests defend, per AC:

  1. `UNIVERSAL_GATES` is *derived* from the registry and byte-identical to the
     literal it replaced. A refactor that quietly flips a severity or drops a
     trigger is a behaviour change wearing a refactor's clothes, so the old
     literal is frozen here by hand — deriving the expectation from the code
     under test would assert only that the code equals itself (convention #266).
  2. Dispatch is a registry lookup: a gate added to the registry at runtime
     executes its own implementation with no edit to `gate_runner`.
  3. Post-scope gates run from the registry, in declaration order.
  4. They appear in `gates status` with a truthful `enabled` — including the
     changelog gate, whose switch is the legacy `task_done.changelog_gate`.
  5. `get_gates_for_trigger` excludes them, so `run_gates` never calls one with
     the wrong signature.
  6. Each post-scope gate writes a `gate_runs` row — the evidence that was
     missing.
  7. "Built-in" comes from the registry, not from `command is None`: `ruff` is
     declared *and* overridable, `filesize` is declared and is not.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import gate_registry as reg  # noqa: E402
import gate_runner  # noqa: E402
from backend_schema_gate_runs import GATE_RUNS_SQL  # noqa: E402
from gate_post_scope import run_post_scope_gates  # noqa: E402

# Bound at import, before conftest's autouse `_mock_run_gates` replaces the
# module attribute with a stub — the same escape `tests/test_gates.py` uses.
# Calling `gate_runner.run_gates` here would test the mock.
from gate_runner import gate_verdict, run_gates  # noqa: E402


# --- AC1: the derived metadata equals the literal it replaced ---------------

# Frozen by hand from scripts/default_gates.py as it stood before the registry
# (commit e69fdd0). Do not regenerate from the registry — see the module
# docstring on why an expectation derived from the subject proves nothing.
_UNIVERSAL_GATES_BEFORE = {
    "ruff": {
        "enabled": True,
        "severity": "block",
        "trigger": ["commit"],
        "command": "ruff check {files}",
        "description": "Lint with ruff before commit",
        "file_extensions": [".py"],
    },
    "mypy": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "mypy {files}",
        "description": "Type-check with mypy before commit",
        "file_extensions": [".py"],
    },
    "filesize": {
        "enabled": True,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": None,
        "description": "Warn if files exceed max_lines threshold",
        "max_lines": 500,  # interim cap raised 400→500 (decision #190)
    },
    "bandit": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["review"],
        "command": "bandit -r {files} -q",
        "description": "Security scan with bandit",
    },
    "tdd_order": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["task-done"],
        "command": None,
        "description": "Verify test files were modified (TDD enforcement)",
    },
    "bootstrap_drift": {
        "enabled": True,
        "severity": "block",
        "trigger": ["task-done"],
        "command": None,
        "description": "Fail if deployed IDE profiles drift from scripts/ source",
    },
    "renar_drift_schema": {
        "enabled": True,
        "severity": "warn",
        "trigger": ["task-done"],
        "command": None,
        "description": "RENAR drift-1: schema validation of SPEC/ADAPT artifacts",
    },
    "renar_drift_provenance": {
        "enabled": True,
        "severity": "warn",
        "trigger": ["task-done"],
        "command": None,
        "description": "RENAR drift-7: stale TC↔requirement (task↔SPEC) provenance",
    },
}


class TestDerivedMetadata:
    def test_universal_gates_unchanged_by_the_refactor(self):
        """Every gate that predated the registry still has its exact config.

        Subset, not equality: the snapshot's job is to catch a "refactor" that
        quietly changes a severity or a trigger, and a MISSING key still fails
        it. Demanding equality would additionally forbid ever ADDING a gate,
        which is the one thing the registry exists to make easy — the next
        author would edit the snapshot to match, and the guard would decay into
        a formality.
        """
        from default_gates import UNIVERSAL_GATES

        for name, expected in _UNIVERSAL_GATES_BEFORE.items():
            assert name in UNIVERSAL_GATES, f"gate '{name}' disappeared from the registry"
            assert UNIVERSAL_GATES[name] == expected, f"gate '{name}' config changed"

    def test_defaults_are_copies_not_registry_aliases(self):
        """A caller mutating a merged gate config must not reach the registry."""
        first = reg.defaults_for_phase(reg.PHASE_SCOPED)
        first["filesize"]["max_lines"] = 1
        first["ruff"]["trigger"].append("review")
        second = reg.defaults_for_phase(reg.PHASE_SCOPED)
        assert second["filesize"]["max_lines"] == 500
        assert second["ruff"]["trigger"] == ["commit"]

    def test_every_spec_impl_resolves(self):
        """A typo in a dotted impl path must fail here, not at close time."""
        for spec in reg.GATE_REGISTRY.values():
            if spec.impl.startswith("svc:"):
                from service_gates import GatesMixin

                assert hasattr(GatesMixin, spec.impl.split(":", 1)[1])
            else:
                assert callable(reg._resolve_dotted(spec.impl))


# --- AC2: dispatch is a lookup, not a chain of ifs --------------------------


class TestDispatch:
    def test_runtime_registry_entry_runs_its_own_impl(self, monkeypatch):
        """The point of the registry: a new gate needs no gate_runner edit."""
        calls = []

        probe = types.ModuleType("_probe_gate_impl")

        def _impl(gate, files):
            calls.append((gate["name"], list(files)))
            return False, "probe says no"

        probe.run = _impl
        monkeypatch.setitem(sys.modules, "_probe_gate_impl", probe)

        spec = reg.GateSpec(
            name="probe",
            phase=reg.PHASE_SCOPED,
            impl="_probe_gate_impl:run",
            default_config={"enabled": True, "severity": "block", "trigger": ["task-done"]},
        )
        monkeypatch.setitem(reg.GATE_REGISTRY, "probe", spec)
        monkeypatch.setattr(
            gate_runner,
            "get_gates_for_trigger",
            lambda *a, **k: [{**spec.default_config, "name": "probe"}],
        )
        monkeypatch.setattr(gate_runner, "load_config", lambda *a, **k: {})

        passed, results = run_gates("task-done", ["a.py"])
        assert calls == [("probe", ["a.py"])]
        assert passed is False
        assert results[0]["output"] == "probe says no"

    def test_gate_with_no_impl_and_no_command_is_skip_not_pass(self, monkeypatch):
        """It used to answer "No command configured." as a PASS — a gate that
        never executed reporting success, the reading `gate_verdict` forbids."""
        gate = {"name": "hollow", "enabled": True, "severity": "block", "trigger": ["task-done"]}
        monkeypatch.setattr(gate_runner, "get_gates_for_trigger", lambda *a, **k: [gate])
        monkeypatch.setattr(gate_runner, "load_config", lambda *a, **k: {})

        _passed, results = run_gates("task-done", ["a.py"])
        assert results[0]["skipped"] is True
        assert gate_verdict(results[0]) == "SKIP"
        assert "ships no implementation" in results[0]["output"]


# --- AC4 / AC5: visible in status, excluded from the scoped runner ----------


class TestVisibilityAndPhaseFilter:
    def test_post_scope_gates_are_listed(self):
        from project_config import load_gates

        gates = load_gates(cfg={})
        assert "verify_first" in gates
        assert "changelog" in gates
        assert gates["verify_first"]["phase"] == reg.PHASE_POST_SCOPE

    def test_changelog_enabled_reflects_the_legacy_switch(self):
        """`gates status` must not call the gate OFF while it blocks every close."""
        from project_config import load_gates

        legacy_on = {"task_done": {"changelog_gate": {"enabled": True}}}
        assert load_gates(cfg=legacy_on)["changelog"]["enabled"] is True
        assert load_gates(cfg={})["changelog"]["enabled"] is False

    def test_scoped_runner_never_sees_a_post_scope_gate(self):
        from project_config import get_gates_for_trigger

        names = [g["name"] for g in get_gates_for_trigger("task-done", cfg={})]
        assert "verify_first" not in names
        assert "changelog" not in names
        assert "filesize" in names  # the filter is narrow, not a blanket drop


# --- AC3 / AC6: the post-scope loop and its evidence ------------------------


class _FakeBackend:
    def __init__(self, conn):
        self._conn = conn
        self.events = []

    def event_add(self, *a, **k):
        self.events.append(a)

    def task_append_notes(self, *a, **k):
        pass


class _FakeService:
    """Minimal stand-in: the loop needs `be`, and `tausik_dir` for config scope.

    The scratch project gets a real `config.json` enabling the changelog gate
    through its legacy key, so `_enabled_map` is exercised for real rather than
    stubbed — the resolution from that key is itself part of what AC4 claims.
    """

    def __init__(self, conn, tmpdir, order, changelog_enabled=True):
        self.be = _FakeBackend(conn)
        self._dir = os.path.join(str(tmpdir), ".tausik")
        os.makedirs(self._dir, exist_ok=True)
        with open(os.path.join(self._dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(
                {"task_done": {"changelog_gate": {"enabled": changelog_enabled}}},
                f,
            )
        self._order = order

    def tausik_dir(self):
        return self._dir

    def _enforce_verify_first(self, report, slug, relevant_files, **kwargs):
        self._order.append("verify_first")

    def _enforce_changelog(self, report, slug, relevant_files=None, **kwargs):
        self._order.append("changelog")
        report["blocking_failures"].append({"gate": "changelog", "output": "no entry"})
        report["passed"] = False


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute(
        "CREATE TABLE verification_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, task_slug TEXT)"
    )
    c.executescript(GATE_RUNS_SQL)
    return c


class TestPostScopeLoop:
    def _report(self):
        return {"passed": True, "results": [], "blocking_failures": []}

    def test_runs_in_declaration_order(self, conn, tmp_path):
        order: list[str] = []
        svc = _FakeService(conn, tmp_path, order)
        run_post_scope_gates(svc, self._report(), "t", ["a.py"])
        assert order == ["verify_first", "changelog"]

    def test_each_gate_leaves_a_gate_runs_row(self, conn, tmp_path):
        """The hole this task closes: the check could not prove a QG-2 gate ran."""
        svc = _FakeService(conn, tmp_path, [])
        run_post_scope_gates(svc, self._report(), "t", ["a.py"])
        rows = dict(
            conn.execute(
                "SELECT gate_name, passed FROM gate_runs WHERE task_slug='t' AND trigger='task-done'"
            ).fetchall()
        )
        assert rows == {"verify_first": 1, "changelog": 0}

    def test_verdict_is_read_from_the_report_not_claimed(self, conn, tmp_path):
        """The changelog stub blocks; its row must say so."""
        svc = _FakeService(conn, tmp_path, [])
        results = run_post_scope_gates(svc, self._report(), "t", ["a.py"])
        by_name = {r["name"]: r for r in results}
        assert by_name["verify_first"]["passed"] is True
        assert by_name["changelog"]["passed"] is False

    def test_fileless_close_skips_changelog_only(self, conn, tmp_path):
        """A task that touched no files carries no changelog diff by construction;
        Verify-First still runs — it is what proves the scope is empty."""
        order: list[str] = []
        svc = _FakeService(conn, tmp_path, order)
        run_post_scope_gates(svc, self._report(), "t", None, no_file_changes=True)
        assert order == ["verify_first"]
        skipped = conn.execute(
            "SELECT skipped FROM gate_runs WHERE gate_name='changelog'"
        ).fetchone()
        assert skipped[0] == 1

    def test_disabling_a_gate_that_ships_on_is_countable(self, monkeypatch, conn, tmp_path):
        """An opt-out may exist; it may not be invisible (l26-bypass-telemetry)."""
        order: list[str] = []
        svc = _FakeService(conn, tmp_path, order)
        monkeypatch.setattr(
            "gate_post_scope._enabled_map",
            lambda _svc: {"verify_first": False, "changelog": True},
        )
        run_post_scope_gates(svc, self._report(), "t", ["a.py"])
        assert order == ["changelog"]
        assert any("bypass_post_scope_gate_verify_first" in a for a in svc.be.events[0])

    def test_unadopted_optin_gate_is_not_reported_as_a_bypass(self, conn, tmp_path):
        """The changelog gate ships OFF. A project that never adopted it is not
        bypassing anything, and saying so on every close would bury the real
        bypasses under noise."""
        order: list[str] = []
        svc = _FakeService(conn, tmp_path, order, changelog_enabled=False)
        run_post_scope_gates(svc, self._report(), "t", ["a.py"])
        assert order == ["verify_first"]
        assert svc.be.events == []
        skipped = conn.execute(
            "SELECT skipped FROM gate_runs WHERE gate_name='changelog'"
        ).fetchone()
        assert skipped[0] == 1  # recorded as never-fired, not as absent

    def test_no_project_directory_leaves_every_gate_on(self, conn, tmp_path):
        """A service with no project handle must not resolve policy from the
        ambient cwd — another repo's config would decide THIS close (memory
        #265). Unknown scope means every gate runs."""
        from gate_post_scope import _enabled_map

        class _Rootless:
            be = None

        assert _enabled_map(_Rootless()) == {}

    def test_malformed_changelog_policy_still_reaches_the_gate(self, conn, tmp_path):
        """A typo must not skip the call whose job is to fail closed on it."""
        from gate_changelog import changelog_gate_enabled

        assert changelog_gate_enabled({"task_done": {"changelog_gate": {"enabled": "yes"}}}) is True

    def test_a_resolver_that_raises_leaves_the_gate_on(self, monkeypatch):
        """This answer gates execution, not just the status line: one unreadable
        key must not be able to retire a QG-2 gate."""
        spec = reg.GATE_REGISTRY["changelog"]
        monkeypatch.setitem(
            reg.GATE_REGISTRY,
            "changelog",
            reg.GateSpec(
                name=spec.name,
                phase=spec.phase,
                impl=spec.impl,
                default_config=spec.default_config,
                enabled_resolver="gate_registry:_raises_for_test",
            ),
        )
        monkeypatch.setattr(
            reg,
            "_raises_for_test",
            lambda _cfg: (_ for _ in ()).throw(RuntimeError("boom")),
            raising=False,
        )
        assert reg.resolve_enabled("changelog", {}, False) is True

    def test_unwritable_evidence_blocks_the_close(self, tmp_path):
        """Convention #221 — a check that cannot record its result must not
        report success. Missing gate_runs table = no evidence = no close."""
        bare = sqlite3.connect(":memory:")
        svc = _FakeService(bare, tmp_path, [])
        report = self._report()
        run_post_scope_gates(svc, report, "t", ["a.py"])
        assert report["passed"] is False
        assert any(f["gate"] == "gate-runs-record" for f in report["blocking_failures"])


# --- AC7: "built-in" is declared, not inferred ------------------------------


class TestBuiltinIsDeclared:
    def test_command_gate_in_the_registry_still_takes_an_override(self):
        """`ruff` is declared here yet IS a command gate: a vendored path or a
        dropped `npx` wrapper stays legal."""
        from gate_command_policy import validate_default_gate_command

        assert reg.is_builtin("ruff") is False
        assert (
            validate_default_gate_command(
                "ruff", "vendor/bin/ruff check {files}", "ruff check {files}"
            )
            is None
        )

    def test_in_process_gate_refuses_an_override(self):
        from gate_command_policy import validate_default_gate_command

        assert reg.is_builtin("filesize") is True
        err = validate_default_gate_command("filesize", "pytest -q", None)
        assert err is not None and "in-process" in err

    def test_post_scope_gate_refuses_an_override(self):
        from gate_command_policy import validate_default_gate_command

        assert reg.is_builtin("verify_first") is True
        assert validate_default_gate_command("verify_first", "pytest -q", None) is not None

    def test_unknown_gate_keeps_the_legacy_inference(self):
        """Stack- and user-declared gates are not in the registry and must keep
        behaving exactly as before."""
        assert reg.is_builtin("some_stack_gate", "phpstan analyse") is False
        assert reg.is_builtin("some_stack_gate", None) is True


class TestNoDispatchChainLeftBehind:
    def test_gate_runner_holds_no_gate_name_branches(self):
        """The chain this task deleted must not grow back one `elif` at a time."""
        src = open(
            os.path.join(os.path.dirname(__file__), "..", "scripts", "gate_runner.py"),
            encoding="utf-8",
        ).read()
        for name in ("filesize", "tdd_order", "bootstrap_drift"):
            assert f'name == "{name}"' not in src

    def test_service_gates_holds_no_hardcoded_post_scope_calls(self):
        src = open(
            os.path.join(os.path.dirname(__file__), "..", "scripts", "service_gates.py"),
            encoding="utf-8",
        ).read()
        assert "self._enforce_verify_first(" not in src
        assert "self._enforce_changelog(" not in src
