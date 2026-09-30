"""The "is code needed" question is a line at task start, and the negative half is why.

The measurement came before the mechanism and changed what got built. Recorded
refusals per month of closure: 3.0% (2026-03), 2.7%, 3.1%, 0.0% (06), then 10.8%
(07), 27.5% (08), 23.3% (09) -- an eightfold rise in three months with no mechanism
whatsoever. So nothing here blocks, nothing here adds a field, and the tests below
spend most of their effort proving that.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from code_necessity import code_necessity_prompt  # noqa: E402


class TestWhereTheQuestionIsAsked:
    @pytest.mark.parametrize("complexity", ["medium", "complex", "MEDIUM", " complex "])
    def test_asked_on_the_larger_tasks(self, complexity):
        """Medium and complex hold 72% of all recorded refusals (117 of 162)."""
        assert code_necessity_prompt({"complexity": complexity, "slug": "s"})

    @pytest.mark.parametrize("complexity", ["simple", None, "", "unknown"])
    def test_silent_everywhere_else(self, complexity):
        """Silence is the point, not an omission.

        Refusal rate on simple tasks is 6.9% (35 of 508), half the rate of medium.
        A line shown on all 508 would be wallpaper by the second week, and then it
        would be wallpaper on the 915 where it earns its place too.
        """
        assert code_necessity_prompt({"complexity": complexity, "slug": "s"}) == ""


class TestItIsASignalAndNotAGate:
    def test_a_missing_complexity_does_not_raise(self):
        """An advisory that can fail is a gate with extra steps."""
        assert code_necessity_prompt({}) == ""

    def test_nothing_is_required_of_the_author(self):
        """The prompt asks; it never names a field to fill.

        AC3 forbids a seventh required field, so the text must not read as one. The
        words a required field would use are the ones checked for.
        """
        text = code_necessity_prompt({"complexity": "medium", "slug": "s"})
        for demand in ("--code-needed", "обязательн", "заполни", "required", "QG-"):
            assert demand not in text


class TestTheAnswerNoLeadsSomewhere:
    def test_the_refusal_path_is_named_with_the_slug(self):
        """AC5: "no code needed" must close the task, not leave it hanging.

        The command is spelled out with this task's own slug, because a prompt that
        says "close it somehow" is how a refusal turns into an abandoned task. The
        mechanism is not new -- `task obsolete --reason` shipped with schema v67 --
        and duplicating it would have been worse than the gap.
        """
        text = code_necessity_prompt({"complexity": "complex", "slug": "migrate-billing"})
        assert "task obsolete migrate-billing" in text
        assert "--reason" in text

    def test_the_order_of_the_three_steps_is_the_content(self):
        """Ask whether code is needed, then look for it, then write it.

        Checked by position rather than by presence: a text carrying all three ideas
        in the wrong order teaches the wrong habit, and that is the one thing this
        line exists to convey.
        """
        text = code_necessity_prompt({"complexity": "medium", "slug": "s"})
        needed = text.index("нужен ли он вообще")
        library = text.index("стандартной библиотеке")
        write = text.index("пишите своё")
        assert needed < library < write


class TestItReachesTheRealTaskStart:
    """The wiring, not the function. A prompt nobody sees is a comment.

    Written against the service rather than the CLI because the CLI only prints what
    the service returns, and a test of the print would pass with the call removed.
    """

    @pytest.fixture
    def svc(self, tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        s = ProjectService(SQLiteBackend(str(tmp_path / "n.db")))
        s.session_start()
        s.epic_add("e", "Epic")
        s.story_add("e", "s", "Story")
        yield s
        s.be.close()

    def _started(self, svc, slug, complexity):
        svc.task_add("s", slug, "T", role="developer", goal="g", complexity=complexity)
        svc.be.task_update(
            slug,
            acceptance_criteria="Returns 400 on invalid input.",
            scope_paths='["scripts/x.py"]',
            rollback_plan="git revert",
        )
        return svc.task_start(slug)

    def test_a_medium_task_start_carries_the_question(self, svc):
        out = self._started(svc, "bigger", "medium")
        assert "Нужен ли код" in out
        assert "task obsolete bigger" in out

    def test_a_simple_task_start_does_not(self, svc):
        """The obvious case stays cheap, which is the whole of AC4."""
        assert "Нужен ли код" not in self._started(svc, "smaller", "simple")
