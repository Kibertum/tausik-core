"""Russian↔English parity of the QG-0 negative-scenario detector.

qg0-negative-detector-russian-parity. The detector knew English `negative` (and
`timeout`, `exception`, `crash`, `exceed`, `overflow`) but not their Russian
counterparts, so a criterion that named its negative case in Russian ("НЕГАТИВ:
...") failed QG-0 in a Russian-language project. Caught by dogfooding on
state-git-export. These pin the parity AND the regression: the `без`/`no`
redaction that makes "Без ошибок" a NON-scenario must stay intact.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import pytest  # noqa: E402

from gate_negative_scenario import has_negative_scenario  # noqa: E402


class TestRussianMarkersAreRecognized:
    @pytest.mark.parametrize(
        "ac",
        [
            "5. НЕГАТИВ: сущность без слага -> экспорт отказывает с ошибкой",
            "2. При таймауте соединения задача не зависает",
            "3. Выбрасывает исключение на битом frontmatter",
            "4. Падение процесса при недоступной БД обрабатывается",
            "5. Крах воркера не роняет сессию",
            "6. Превышение лимита строк блокируется",
            "7. Переполнение очереди отклоняется",
        ],
    )
    def test_a_russian_negative_criterion_passes(self, ac):
        assert has_negative_scenario(ac) is True, ac

    def test_the_dogfood_case_that_exposed_it(self):
        # The exact state-git-export criterion that failed QG-0.
        ac = (
            "5. НЕГАТИВ: сущность без слага -> export ОТКАЗЫВАЕТ с явной "
            "ошибкой 'нужна миграция', не молча пропускает."
        )
        assert has_negative_scenario(ac) is True


class TestParityWithEnglish:
    @pytest.mark.parametrize(
        "ru, en",
        [
            ("Сценарий: негатив покрыт", "Scenario: negative covered"),
            ("Таймаут обработан", "Timeout handled"),
            ("Исключение поймано", "Exception caught"),
        ],
    )
    def test_same_verdict_in_both_languages(self, ru, en):
        assert has_negative_scenario(ru) == has_negative_scenario(en) is True


class TestRedactionRegressionStillHolds:
    """The `без`/`without` cancel must survive the keyword additions — a criterion
    that says the negative will NOT happen is not a negative scenario."""

    def test_bez_oshibok_is_not_a_scenario(self):
        assert has_negative_scenario("1. Работает. 2. Без ошибок.") is False

    def test_without_errors_is_not_a_scenario(self):
        assert has_negative_scenario("Works without any errors") is False
        assert has_negative_scenario("Works without crashing") is False
        assert has_negative_scenario("No failures during prod load") is False

    def test_a_plain_positive_criterion_is_not_a_scenario(self):
        # None of the new stems fire on ordinary prose (guards against a stem that
        # matches an unrelated word — e.g. 'сбор'/'сборка' were deliberately NOT added).
        assert has_negative_scenario("1. Сборка проходит. 2. Сбор метрик работает.") is False


class TestNegativeWordParityWithEvidenceDetector:
    """qg0-negative-detector-does-not-know-the-word-negative (#301).

    The framework has TWO negativity detectors answering the same question at
    two lifecycle points: `NEGATIVE_RE` (task-done evidence) and
    `has_negative_scenario` (QG-0 start). They diverged — QG-0 knew `negative`
    and `негативн` but not `отрицательн`, so a criterion naming its negative
    case as "отрицательный" passed the evidence check yet was BLOCKED at start.
    These pin the single-source invariant EXECUTABLY: the negative-WORD forms
    are read from `NEGATIVE_RE` itself, so adding a form there without teaching
    QG-0 fails this test instead of silently reopening the split.
    """

    def _neg_word_stems(self) -> list[str]:
        # Producer-derived: parse NEGATIVE_RE's alternation into base stems so a
        # new form added there is picked up here automatically (session #134
        # warning: a test that enumerates the set it guards cannot see it grow).
        from ac_evidence_detectors import NEGATIVE_RE

        stems = []
        for part in NEGATIVE_RE.pattern.split("|"):
            s = part.replace(r"\b", "").replace(r"\w*", "").strip()
            if s:
                stems.append(s)
        return stems

    def test_the_previously_missing_russian_form_now_passes(self):
        # AC1: the exact form the task named — was False before the fix.
        assert has_negative_scenario("1. отрицательный результат обрабатывается") is True

    def test_every_evidence_negative_word_is_a_qg0_scenario(self):
        from ac_evidence_detectors import NEGATIVE_RE

        stems = self._neg_word_stems()
        assert stems, "NEGATIVE_RE alternation parse produced no stems — scan broke"
        for stem in stems:
            # A concrete criterion using this negative word. The stem is a
            # substring of the sample, so both detectors should fire on it.
            sample = f"1. Проверяется {stem}ый случай и обрабатывается"
            if stem == "negative":
                sample = "1. A negative case is exercised and handled"
            assert NEGATIVE_RE.search(sample), f"NEGATIVE_RE lost its own form {stem!r}"
            assert has_negative_scenario(sample) is True, (
                f"QG-0 does not recognise the negative-word form {stem!r} that the "
                "evidence detector NEGATIVE_RE does — the two detectors diverged."
            )
