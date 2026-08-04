"""Recording a decision never publishes it. Visibility is chosen, not inferred.

`decide` used to run the text through a classifier that looked for
project-specific markers and mirrored anything general-looking to Notion. The
rule was not badly written; it was the wrong KIND of rule. Visibility is a
judgement about intent, and no reader of the words can recover it — the same
sentence is a private note in one project and a lesson worth sharing in another,
and only the author knows which.

It failed in the direction that costs something: six of this project's own
internal decisions reached the owner's wiki, including the one cancelling the
2.0 plan and the one about the release date, each with the reason "no
project-specific markers detected" — because a well-written decision is usually
phrased generally.

These tests are written so that wiring any inference back in fails them.
"""

from __future__ import annotations

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

CROSSCUTTING_SCOPE = ["scripts/service_decide.py", "scripts/brain_move.py"]

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")

# Phrased exactly the way the old classifier rewarded: general, no
# three-segment slugs, no file paths. This is the text that used to escape.
GENERAL_SOUNDING = (
    "Оценку срока нельзя строить на коэффициенте, чей разброс больше "
    "объясняемого им эффекта — иначе прогноз отражает шум, а не работу."
)


def _source(name: str) -> str:
    with open(os.path.join(_SCRIPTS, name), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture
def svc(tmp_path, monkeypatch):
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    root = tmp_path / "proj"
    (root / ".tausik").mkdir(parents=True)
    monkeypatch.chdir(root)
    monkeypatch.setenv("TAUSIK_DIR", str(root / ".tausik"))
    service = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
    yield service
    service.be.close()


class TestRecordingNeverPublishes:
    """AC1: no text, however general, reaches the wiki by being recorded."""

    def test_a_general_sounding_decision_stays_local(self, svc, monkeypatch):
        """The exact shape that used to escape, with the wiki fully enabled."""
        import brain_config
        import brain_mcp_write

        monkeypatch.setattr(
            brain_config, "load_brain", lambda *a, **k: {"enabled": True}, raising=False
        )
        monkeypatch.setattr(
            brain_mcp_write,
            "store_record",
            lambda *a, **k: pytest.fail("recording a decision published it to Notion"),
        )

        out = svc.decide(GENERAL_SOUNDING)
        assert "local" in out.lower()
        assert len(svc.decisions()) == 1

    def test_the_classifier_is_not_consulted_at_all(self, svc, monkeypatch):
        """Not "it decided correctly" — it is not asked.

        A classifier that happens to answer "local" today is one config change
        away from answering otherwise. The property is that the question is
        never put to it.
        """
        import brain_classifier

        monkeypatch.setattr(
            brain_classifier,
            "classify",
            lambda *a, **k: pytest.fail("the publication route still consults the classifier"),
        )
        svc.decide(GENERAL_SOUNDING)
        assert len(svc.decisions()) == 1

    def test_recording_does_not_import_the_classifier(self):
        """Structural: `record` must not reference it, so it cannot creep back."""
        tree = ast.parse(_source("service_decide.py"))
        fn = next(
            n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "record"
        )
        names = {
            alias.name
            for node in ast.walk(fn)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        assert "classify" not in names, (
            "`record` imports the classifier again — visibility is being inferred "
            "from the text instead of chosen by the author"
        )

    @pytest.mark.parametrize("rationale", [None, "обоснование без маркеров проекта"])
    def test_neither_headline_nor_rationale_changes_the_destination(
        self, svc, monkeypatch, rationale
    ):
        import brain_mcp_write

        monkeypatch.setattr(
            brain_mcp_write,
            "store_record",
            lambda *a, **k: pytest.fail("a rationale routed the decision outward"),
        )
        svc.decide(GENERAL_SOUNDING, None, rationale)
        assert len(svc.decisions()) == 1


class TestPublishingKeepsTheLocalCopy:
    """AC5(a): publishing is a MIRROR. Found before shipping, not after.

    With automatic mirroring gone, `brain move --to-brain` is the path a person
    is pointed at — and it deleted the local row by default. A publish that
    removes the project's copy is a handover, and it contradicts the first
    guarantee of `service_decide`: the project's own copy is unconditional.
    """

    def test_keeping_the_source_is_the_default(self):
        tree = ast.parse(_source("brain_move.py"))
        fn = next(
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "move_to_brain"
        )
        kwonly = {a.arg: d for a, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults)}
        assert "keep_source" in kwonly, "the keep_source contract disappeared"
        default = kwonly["keep_source"]
        assert isinstance(default, ast.Constant) and default.value is True, (
            "publishing deletes the local decision by default — that is a handover, "
            "not a publish, and it breaks the unconditional local copy"
        )

    def test_the_cli_offers_an_explicit_way_to_move_instead(self):
        """Handing a record over stays possible — under a name that says so."""
        src = _source("project_parser_brain.py")
        assert "--drop-local" in src
        assert "--keep-source" in src, "removing the old flag would break existing scripts"


class TestNotionRemainsOptional:
    """AC3: with the wiki off, none of this is reachable — and nothing is lost."""

    def test_a_decision_is_recorded_with_the_brain_disabled(self, svc, monkeypatch):
        import brain_config

        monkeypatch.setattr(
            brain_config, "load_brain", lambda *a, **k: {"enabled": False}, raising=False
        )
        svc.decide("решение при выключенном brain")
        assert len(svc.decisions()) == 1

    def test_the_record_path_does_not_open_the_wiki_at_all(self, svc, monkeypatch):
        """Not merely "it does not publish" — it does not even connect."""
        import brain_runtime

        monkeypatch.setattr(
            brain_runtime,
            "open_brain_deps",
            lambda *a, **k: pytest.fail("recording a decision opened the brain"),
        )
        svc.decide("обычное решение")
        assert len(svc.decisions()) == 1
