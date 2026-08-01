"""`decide` must judge by what leaves the machine, not by its headline.

The router classified `text` alone while the publish payload also carried
`rationale`. A good rationale is by definition dense with project detail, so the
one field that most identifies an internal decision was the one field never
consulted. Live consequence (session #152): a decision recording this release's
own scope was published to Notion and left no trace in the project.

The marker rule itself was fine. `memory_markers` drops two-segment slugs
(`shared-knowledge`, `doc-swarm`) as indistinguishable from English kebab
compounds unless a three-segment slug corroborates them in the same text — and
the corroborating slugs (`redoc-1-8-final`, `l26-memory-decay`) lived in the
rationale. Right rule, half the evidence.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_classifier  # noqa: E402
import brain_publish_flow  # noqa: E402
from brain_runtime import decision_publish_fields  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

# The live payload that escaped, trimmed to the part that decides the verdict.
HEADLINE = (
    "Решение #161 подтверждено владельцем: релиз 1.8 НЕ готов. shared-knowledge "
    "и финальный гейт doc-swarm входят в объём. Тег v1.8.0 не ставится."
)
RATIONALE = (
    "Факт: landscape 76/77, shared-knowledge 2/25, doc-swarm не запускался "
    "(подменён redoc-1-8-final без решения). #195 не выводил l26-memory-decay из 1.8."
)

BRAIN_CFG = {
    "enabled": True,
    "notion_integration_token_env": "TEST_TOKEN",
    "database_ids": {"decisions": "db-dec-1"},
}


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """A well-formed project: the tmp DB IS this project's DB for the test."""
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir(parents=True, exist_ok=True)
    be = SQLiteBackend(str(tausik_dir / "tausik.db"))
    s = ProjectService(be)
    import project_config

    monkeypatch.setattr(project_config, "find_tausik_dir", lambda *a, **k: str(tausik_dir))
    yield s
    be.close()


# --- the classifier is fed the whole payload ---------------------------------


def test_headline_alone_would_route_to_brain():
    """The premise, pinned: judging by the headline is what sent it out.

    If this ever flips to 'local', the defect below stops being reproducible and
    the test after it would pass for the wrong reason.
    """
    assert brain_classifier.classify(HEADLINE, "decision").target == "brain"


def test_full_payload_routes_local():
    blob = HEADLINE + "\n" + RATIONALE
    d = brain_classifier.classify(blob, "decision")
    assert d.target == "local"
    assert any(m.kind == "slug" for m in d.markers)


def test_decide_classifies_the_published_payload(svc, monkeypatch):
    """End to end: rationale-only project detail keeps the decision at home."""
    seen: dict[str, str] = {}
    real = brain_classifier.classify

    def spy(content, category, **kw):
        seen["blob"] = content
        return real(content, category, **kw)

    monkeypatch.setattr(brain_classifier, "classify", spy)
    with (
        patch("brain_config.load_brain", return_value=BRAIN_CFG),
        patch("brain_config.validate_brain", return_value=[]),
        patch("brain_runtime.try_brain_write_decision") as mock_brain,
    ):
        msg = svc.decide(HEADLINE, rationale=RATIONALE)

    mock_brain.assert_not_called()  # never left the machine
    assert "saved to local" in msg
    assert RATIONALE in seen["blob"], "the rationale must reach the classifier"


def test_classified_blob_covers_every_published_field(svc, monkeypatch):
    """Ratchet: a field added to the payload cannot escape classification.

    Both sides derive from `decision_publish_fields`, so this holds structurally
    — the test exists to fail loudly if someone re-splits them.
    """
    seen: dict[str, str] = {}

    def spy(content, _category, **_kw):
        seen["blob"] = content
        return brain_classifier.Decision("local", "spy", [], None)

    monkeypatch.setattr(brain_classifier, "classify", spy)
    with (
        patch("brain_config.load_brain", return_value=BRAIN_CFG),
        patch("brain_config.validate_brain", return_value=[]),
    ):
        svc.decide("Заголовок решения", rationale="Обоснование решения")

    for key, value in decision_publish_fields("Заголовок решения", "Обоснование решения").items():
        assert str(value) in seen["blob"], f"published field {key!r} never reached the classifier"


# --- an external publish must not fire from a throwaway context --------------


def test_foreign_db_never_publishes(tmp_path, monkeypatch):
    """A service bound to a DB that is not the project's cannot write outward.

    Reproduced before the guard: `decide` on a temp DB created a live page in the
    user's Notion. A one-off context whose whole premise is that nothing outside
    it changes must not reach a shared store.
    """
    stray = ProjectService(SQLiteBackend(str(tmp_path / "stray.db")))
    real_dir = tmp_path / "elsewhere" / ".tausik"
    real_dir.mkdir(parents=True, exist_ok=True)
    import project_config

    monkeypatch.setattr(project_config, "find_tausik_dir", lambda *a, **k: str(real_dir))
    try:
        with (
            patch("brain_config.load_brain", return_value=BRAIN_CFG),
            patch("brain_config.validate_brain", return_value=[]),
            patch("brain_runtime.try_brain_write_decision") as mock_brain,
        ):
            msg = stray.decide("Prefer exponential backoff for network retries")
        mock_brain.assert_not_called()
        assert "not bound to the project DB" in msg  # the real reason, not a stand-in
        assert len(stray.decisions()) == 1  # still recorded locally
    finally:
        stray.be.close()


def test_unknown_db_provenance_fails_closed(svc, monkeypatch):
    """If the project dir cannot be resolved at all, do not publish."""
    import project_config

    def _boom(*_a, **_kw):
        raise RuntimeError("no project here")

    monkeypatch.setattr(project_config, "find_tausik_dir", _boom)
    with (
        patch("brain_config.load_brain", return_value=BRAIN_CFG),
        patch("brain_config.validate_brain", return_value=[]),
        patch("brain_runtime.try_brain_write_decision") as mock_brain,
    ):
        svc.decide("Prefer exponential backoff for network retries")
    mock_brain.assert_not_called()


def test_genuinely_cross_project_decision_still_publishes(svc):
    """NEGATIVE for the fix: the legit path is not collateral damage."""
    with (
        patch("brain_config.load_brain", return_value=BRAIN_CFG),
        patch("brain_config.validate_brain", return_value=[]),
        patch(
            "brain_runtime.try_brain_write_decision", return_value=(True, "page-1")
        ) as mock_brain,
    ):
        msg = svc.decide(
            "Prefer exponential backoff over fixed retry intervals",
            rationale="Fixed intervals synchronise retries across clients and amplify load.",
        )
    mock_brain.assert_called_once()
    assert "mirrored to brain" in msg
    assert len(svc.decisions()) == 1  # mirrored, not moved


# --- decisions are inside the risk gate now ----------------------------------


def test_decisions_are_subject_to_the_publish_risk_gate():
    """`decisions` had no entry, so the gate returned early for every one."""
    fields = decision_publish_fields(HEADLINE, RATIONALE)
    level, _ = brain_publish_flow.assess_publish_risk("decisions", fields, {})
    assert level == "high"
    blocked, message = brain_publish_flow.maybe_block_high_risk_publish(
        "decisions", fields, {}, confirm_high_risk=False
    )
    assert blocked and message and "project-specific" in message


def test_generic_decision_is_not_blocked_by_the_risk_gate():
    fields = decision_publish_fields(
        "Prefer exponential backoff over fixed retry intervals",
        "Fixed intervals synchronise retries across clients.",
    )
    blocked, _ = brain_publish_flow.maybe_block_high_risk_publish(
        "decisions", fields, {}, confirm_high_risk=False
    )
    assert not blocked


def test_unregistered_category_refuses_to_borrow_another_categorys_keys():
    """The blob builder used to fall back to gotcha keys for ANY category.

    Silently, and with a plausible-looking result: a category whose fields share
    no key with gotchas yields a blob of empty strings, which classifies as
    "empty content" → local → high risk → every publish of that category blocked
    for a reason no message would ever explain.
    """
    with pytest.raises(KeyError, match="no classifier text keys registered"):
        brain_publish_flow.artifact_blob_for_classifier("snippets", {"name": "x"})


# --- the binding guard answers "same FILE", not "same string" ----------------


def _spelling_variant(path: str) -> str:
    r"""The same file, spelled differently. NEVER the input unchanged.

    This used to return the path untouched on POSIX, which turned two of the
    tests below into "is X the same file as X" on two of the three CI legs — a
    tautology dressed as a regression test, with the real coverage resting on
    windows-latest alone.

    Each platform gets the variant its own resolver has to earn:

      * Windows hands out `d:\...` or `D:\...` depending on which API produced
        the path, and both name one file. `normcase` is what makes them equal,
        so flipping the drive letter is what puts `normcase` on trial.
      * POSIX has no case variant — `os.path.normcase` is the identity there, so
        no probe can make its removal redden a POSIX run, and pretending
        otherwise would be the same false claim one level up. What CAN be put on
        trial is the other half of the guard: `<dir>/./<base>` and a `..` round
        trip name the same file through a different string, and only `realpath`
        collapses them. A string comparison fails on both.

    So on every platform the returned string DIFFERS from the input, and
    `_same_file` has to do real work to call them equal — which is exactly the
    claim the class below is named for.
    """
    if len(path) > 1 and path[1] == ":":
        head = path[0]
        return (head.upper() if head.islower() else head.lower()) + path[1:]
    head, tail = os.path.split(path.rstrip(os.sep))
    if not tail:
        return path
    return os.path.join(head, ".", tail, "..", tail)


class TestBindingGuardComparesFilesNotStrings:
    r"""A drive-letter difference used to disable publishing AND misreport why.

    The guard is fail-closed, so `d:\` against `D:\` did not merely fail to
    publish — it routed through `local_reason`'s last branch and told a user
    working inside their own project that the context was a throwaway. Both
    halves are pinned here, because the message was rewritten in #152
    specifically so it would stop naming a reason that was not the reason.
    """

    def test_the_variant_is_never_the_input_unchanged(self, tmp_path):
        """The tautology guard, and it is mechanical rather than a promise.

        On POSIX this helper used to hand back its argument, so the two tests
        below asserted that a path equals itself. That could only be noticed by
        reading the helper; now it is noticed by running the suite on any
        platform, which is the leg that was missing.
        """
        original = str(tmp_path / ".tausik")
        variant = _spelling_variant(original)
        assert variant != original, "the variant must differ AS A STRING, or nothing is tested"
        assert os.path.realpath(variant) == os.path.realpath(original), (
            "and it must still name the same file, or the test asks the wrong question"
        )

    def test_case_differing_drive_letter_is_the_same_project_db(self, tmp_path, monkeypatch):
        from service_decide import is_working_project_db

        tausik_dir = tmp_path / ".tausik"
        tausik_dir.mkdir(parents=True, exist_ok=True)
        db = tausik_dir / "tausik.db"
        be = SQLiteBackend(str(db))
        import project_config

        monkeypatch.setattr(
            project_config, "find_tausik_dir", lambda *a, **k: _spelling_variant(str(tausik_dir))
        )
        try:
            assert is_working_project_db(be) is True
        finally:
            be.close()

    def test_the_throwaway_message_is_unreachable_for_a_casing_difference(
        self, tmp_path, monkeypatch
    ):
        """AC-5: the user is not told their own project is a one-off context.

        The text is deliberately the cross-project one. Feeding it a
        project-specific payload would make the classifier route local on its
        own, and the assertion would pass without the binding guard ever being
        consulted — green for a reason that has nothing to do with the bug.
        """
        tausik_dir = tmp_path / ".tausik"
        tausik_dir.mkdir(parents=True, exist_ok=True)
        s = ProjectService(SQLiteBackend(str(tausik_dir / "tausik.db")))
        import project_config

        monkeypatch.setattr(
            project_config, "find_tausik_dir", lambda *a, **k: _spelling_variant(str(tausik_dir))
        )
        try:
            with (
                patch("brain_config.load_brain", return_value=BRAIN_CFG),
                patch("brain_config.validate_brain", return_value=[]),
                patch("brain_runtime.try_brain_write_decision", return_value=(True, "page-1")),
            ):
                msg = s.decide("Prefer exponential backoff for network retries")
            assert "not bound to the project DB" not in msg
            assert "throwaway" not in msg
            assert "mirrored to brain" in msg  # the guard let it through, as it must
        finally:
            s.be.close()

    def test_a_symlinked_tausik_dir_is_still_the_project(self, tmp_path, monkeypatch):
        """AC-3: the symlink question is decided, not left to chance.

        A link to the project's database IS the project's database; refusing it
        would be the casing over-refusal one indirection further out. Skipped
        where the platform will not let this process create a link (Windows
        without Developer Mode) — the decision is still recorded in the
        docstring of `_same_file`, which is what AC-3 asks for.
        """
        from service_decide import is_working_project_db

        real = tmp_path / "real" / ".tausik"
        real.mkdir(parents=True, exist_ok=True)
        be = SQLiteBackend(str(real / "tausik.db"))
        link = tmp_path / "linked"
        try:
            os.symlink(str(real), str(link), target_is_directory=True)
        except (OSError, NotImplementedError, AttributeError):
            be.close()
            pytest.skip("this platform/process cannot create a directory symlink")
        import project_config

        monkeypatch.setattr(project_config, "find_tausik_dir", lambda *a, **k: str(link))
        try:
            assert is_working_project_db(be) is True
        finally:
            be.close()

    def test_a_genuinely_foreign_db_is_still_refused(self, tmp_path, monkeypatch):
        """NEGATIVE: the guard is not loosened, only made to answer the right question.

        A different DIRECTORY stays foreign however the paths are spelled — the
        two normalizations can only merge spellings of one file, never two files.
        """
        from service_decide import is_working_project_db

        real = tmp_path / "mine" / ".tausik"
        real.mkdir(parents=True, exist_ok=True)
        stray = SQLiteBackend(str(tmp_path / "stray.db"))
        import project_config

        monkeypatch.setattr(project_config, "find_tausik_dir", lambda *a, **k: str(real))
        try:
            assert is_working_project_db(stray) is False
        finally:
            stray.close()
