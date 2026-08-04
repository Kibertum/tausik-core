"""The throwaway-context guard: identity of a FILE, asked of the filesystem.

This file was named for `decide`'s automatic mirror to Notion — which text a
classifier judged publishable and which it kept local. That behaviour is gone
(decision #221): visibility is chosen by the author now, never inferred from the
words, so there is no classification left to test and those five tests were
removed rather than adapted.

What remains is the guard they shared a file with, and it matters MORE than
before. `is_working_project_db` answers "is this service really speaking for the
project", and its caller moved to `brain_move` — which now owns the only path by
which a record leaves this machine. The name of the file is kept so the history
stays findable; the subject is the guard.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

# The publish-risk-gate tests at the bottom of this file are the only coverage
# `brain_publish_flow` has, and the resolver maps a module to `test_<module>.py`
# by name — which this file, kept under its historical name, does not match. So
# `verify --relevant-files scripts/brain_publish_flow.py` ran nine unrelated
# files and none of the gate's own, and reported green. Declared explicitly
# rather than by renaming the file, because the name is what keeps the history
# of decision #221 findable.
CROSSCUTTING_SCOPE = [
    "scripts/brain_publish_flow.py",
    "scripts/service_knowledge.py",
]

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


# --- an external publish must not fire from a throwaway context --------------


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
