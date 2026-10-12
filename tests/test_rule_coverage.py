"""Which rules hold on a host without hooks — asked rule by rule, and proven.

kilo-enforcement-through-the-mcp-boundary. Session #230 made the enforcement
notice honest per HOST: on Kilo it says everything below is instructions. True,
and coarser than the truth. Closing a task without a receipt IS refused on Kilo,
because closing goes through our tool. Writing a file without a task is NOT,
because the host's own editor writes it and we never see the call. One sentence
about a whole host cannot carry both answers.

MEASURED FIRST (session #232, AST over the MCP package): 146 declared tools, 44
mutating handlers, and not one reaching the backend directly. The service layer's
refusals already travel to the MCP boundary — so this file's job is to PROVE
that, at the boundary rather than one layer beneath it, and to hold the per-rule
statement to what it can actually demonstrate.

The two failures that matter are opposite, and both are checked:
  * OVER-claiming — saying a rule is enforced where nothing can see the action.
    The first version of `coverage_for_host` did exactly this, reporting OpenCode
    as covering all three interception rules on the strength of a plugin that
    implements one.
  * UNDER-claiming — telling a Kilo user that nothing below is checked, when
    every closure, every knowledge write and every task opening is refused.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_REPO = os.path.join(os.path.dirname(__file__), "..")
_MCP = os.path.join(_REPO, "harness", "claude", "mcp", "project")
for _p in (os.path.join(_REPO, "scripts"), os.path.join(_REPO, "bootstrap"), _MCP):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import handlers  # noqa: E402
import rule_coverage as rc  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/rule_coverage.py", "harness/claude/mcp/project/"]


def _service(tmp_path, monkeypatch):
    """A project with a database and nothing else — the shape of a fresh install.

    No profile directory is created, deliberately: the whole claim under test is
    that these refusals do not depend on one.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TAUSIK_QUIET", "1")
    return ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))


def _dispatch() -> dict:
    """The tool table exactly as the server assembles it."""
    table = getattr(handlers, "_DISPATCH", None)
    assert isinstance(table, dict) and table, "the MCP dispatch table is empty"
    return table


class TestEverySurfaceClaimIsProvenAtTheBoundary:
    """AC2: driven through the MCP handler, not through the service layer.

    "It works through the CLI, so it works through MCP" is an assumption, and it
    is the assumption the whole task rests on. Assumptions get driven here.
    """

    def test_every_surface_rule_names_a_tool_the_server_actually_serves(self):
        table = _dispatch()
        for rule in rc.RULES:
            if rule.kind != rc.SURFACE:
                continue
            assert rule.carried_by in table, (
                f"{rule.rule} claims to be carried by {rule.carried_by}, which the "
                "MCP server does not serve — the claim cannot be true"
            )

    def test_qg0_refuses_through_the_mcp_handler(self, tmp_path, monkeypatch):
        """Opening a task with no goal and no criteria, via the tool a Kilo agent
        would call."""
        svc = _service(tmp_path, monkeypatch)
        svc.task_add(None, "bare", "No goal, no criteria", role="developer")
        with pytest.raises(ServiceError):
            _dispatch()["tausik_task_start"](svc, {"slug": "bare"})

    def test_qg2_refuses_through_the_mcp_handler(self, tmp_path, monkeypatch):
        """Closing without a fresh signed verification, via the same door.

        THE REFUSAL ARRIVES AS DATA, not as an exception, and that is by design:
        the structured report exists so a non-Claude tool loop can parse a
        refusal instead of pattern-matching an error string. So the assertion is
        the FACT the guarantee rests on — the task does not close — with the
        report as corroboration. An earlier version of this test demanded an
        exception and would have called a working refusal a defect.
        """
        svc = _service(tmp_path, monkeypatch)
        svc.task_add(None, "t", "A task", role="developer", goal="g")
        svc.task_update("t", acceptance_criteria="AC1. Works. AC2 (negative). Fails loudly.")
        _dispatch()["tausik_task_start"](svc, {"slug": "t"})

        report = json.loads(_dispatch()["tausik_task_done"](svc, {"slug": "t", "ac_verified": True}))

        assert svc.task_show("t")["status"] == "active", "the task closed without a receipt"
        assert report["ok"] is False
        failures = " ".join(str(f) for f in report.get("blocking_failures") or [])
        assert "QG-2" in failures, f"the refusal does not name the rule it enforces: {failures}"

    def test_the_refusals_do_not_depend_on_a_deployed_hook(self, tmp_path, monkeypatch):
        """The point of the whole task: these fire in a project with NO profile
        directory at all, which is the shape of a Kilo install."""
        assert not any(
            os.path.isdir(os.path.join(str(tmp_path), d))
            for d in (".claude", ".kilo", ".cursor", ".opencode", ".qwen")
        )
        svc = _service(tmp_path, monkeypatch)
        svc.task_add(None, "bare", "No goal", role="developer")
        with pytest.raises(ServiceError):
            _dispatch()["tausik_task_start"](svc, {"slug": "bare"})


class TestTheClassificationIsDerivedFromTheDeployment:
    def _dir(self, ide: str) -> str | None:
        from enforcement_coverage import profile_dir_for

        return profile_dir_for(_REPO, ide)

    def test_a_host_with_the_full_hook_set_intercepts_everything(self):
        rows = dict(rc.coverage_for_host(self._dir("claude")))
        for rule in rc.RULES:
            expected = rc.SURFACE if rule.kind == rc.SURFACE else "realtime"
            assert rows[rule] == expected, f"{rule.rule}: {rows[rule]}"

    def test_a_host_with_one_plugin_covers_ONLY_what_that_plugin_carries(self):
        """AC4, the over-claim direction. OpenCode ships the QG-0 plugin and
        nothing else; reporting it as covering scope boundaries and the secret
        scan would be the imitation this task forbids."""
        rows = {r.rule: holds for r, holds in rc.coverage_for_host(self._dir("opencode"))}
        assert rows["Rule 1 Task before code"] == "realtime"
        assert rows["Rule 2 Scope Boundaries"] == rc.NEEDS_INTERCEPTION
        assert rows["Rule 10.12 Secret scan"] == rc.NEEDS_INTERCEPTION

    @pytest.mark.parametrize("ide", ["kilo", "cursor"])
    def test_a_host_with_no_mechanism_still_keeps_every_surface_rule(self, ide):
        """AC4, the under-claim direction. Saying 'nothing here is checked' to a
        Kilo user is false about every closure they will ever make."""
        rows = {r.rule: holds for r, holds in rc.coverage_for_host(self._dir(ide))}
        assert rows["QG-0 Context Gate"] == rc.SURFACE
        assert rows["QG-2 Implementation Gate"] == rc.SURFACE
        assert rows["Memory routing"] == rc.SURFACE
        assert rows["Rule 1 Task before code"] == rc.NEEDS_INTERCEPTION

    def test_removing_the_artifact_moves_the_rule(self, tmp_path):
        """The mutation. A classification that survives its evidence being
        deleted is not derived from anything."""
        import json

        profile = tmp_path / ".claude"
        profile.mkdir()
        (profile / "settings.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {"matcher": "Write", "hooks": [{"command": "py hooks/task_gate.py"}]}
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        before = {r.rule: h for r, h in rc.coverage_for_host(str(profile))}
        assert before["Rule 1 Task before code"] == "realtime"
        (profile / "settings.json").unlink()
        after = {r.rule: h for r, h in rc.coverage_for_host(str(profile))}
        assert after["Rule 1 Task before code"] == rc.NEEDS_INTERCEPTION


class TestTheArtifactNamesCannotRot:
    """Decision #335, both directions, against the real generators."""

    def _all_deployed(self) -> set[str]:
        from bootstrap_config import SCAFFOLD_IDES
        from enforcement_coverage import profile_dir_for

        found: set[str] = set()
        for ide in SCAFFOLD_IDES:
            found |= rc.deployed_artifacts(profile_dir_for(_REPO, ide))
        return found

    def test_every_named_artifact_is_one_some_host_really_deploys(self):
        deployed = self._all_deployed()
        for rule in rc.RULES:
            for name in rule.artifacts:
                assert name in deployed, (
                    f"{rule.rule} names {name}, which no scaffolded host deploys — "
                    "the entry describes an intention, not a mechanism"
                )

    def test_every_interception_rule_names_at_least_one_artifact(self):
        for rule in rc.RULES:
            if rule.kind == rc.NEEDS_INTERCEPTION:
                assert rule.artifacts, f"{rule.rule} says it needs interception and names nothing"

    def test_every_surface_rule_names_no_artifact(self):
        """A surface rule carried by an artifact would be two claims about one
        rule, and the weaker one would win silently."""
        for rule in rc.RULES:
            if rule.kind == rc.SURFACE:
                assert not rule.artifacts, f"{rule.rule} is SURFACE and names an artifact"


class TestTheNoticeSaysBothHalves:
    def test_a_host_without_interception_names_the_unenforced_rules(self):
        from enforcement_coverage import profile_dir_for

        text = rc.render_rule_notice(profile_dir_for(_REPO, "kilo"))
        assert "Rule 1 Task before code" in text
        assert "Rule 2 Scope Boundaries" in text
        assert "NOT enforced here" in text

    def test_it_also_says_what_IS_enforced_there(self):
        from enforcement_coverage import profile_dir_for

        text = rc.render_rule_notice(profile_dir_for(_REPO, "kilo"))
        assert "tausik_" in text and "every host" in text, (
            "the notice lists what is unenforced and forgets what is — which "
            "understates the product to the one user who most needs the truth"
        )

    def test_a_fully_covered_host_gets_no_paragraph_at_all(self):
        """Nothing to declare, so nothing is printed. A paragraph that says
        'everything is fine' on every page is one readers learn to skip."""
        from enforcement_coverage import profile_dir_for

        assert rc.render_rule_notice(profile_dir_for(_REPO, "claude")) == ""
