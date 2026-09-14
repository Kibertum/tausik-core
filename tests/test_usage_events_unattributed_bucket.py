"""Корзина «вне задачи»: событие, которое никто не заявил, обязано быть ВИДНО.

usage-attribution-is-keyed-by-task-not-session, негативный сценарий задачи.

ЗАЧЕМ ОТДЕЛЬНЫЙ ФАЙЛ, А НЕ ПАРА УТВЕРЖДЕНИЙ В ТЕСТЕ ХУКА. Миграция v48 сняла
`NOT NULL` с `usage_events.session_id`, и хук перестал дропать событие, у
которого нет открытой сессии. Само по себе это ещё не победа: строка, которая
записалась, но не попадает НИ В ОДИН отчёт, отличается от дропнутой только тем,
что занимает место на диске. Пофункциональный ролап по задачам спрашивает
`WHERE task_slug IS NOT NULL` — и спрашивает правильно, именно эта оговорка не
даёт ему удваивать суммы, — значит дополнение к нему невидимо ПО ПОСТРОЕНИЮ.
Отсюда требование задачи: явная корзина, видимая в `tausik metrics cost`.

ЧТО ИМЕННО ПИНАЕТСЯ ЗДЕСЬ, И ПОЧЕМУ ИМЕННО ЭТО:

1. Корзина считает событие без задачи (и отдельно — сколько из них ещё и без
   сессии). Это половина «строка записана и посчитана».
2. Корзина НЕ включает зеркальные строки `source='session_record'`. Без этого
   фильтра отчёт вернул бы ту самую ~2x ошибку, против которой написан
   test_usage_events_double_count.py: сессионная строка равна сумме posttool-
   строк и всегда несёт NULL task_slug, то есть попала бы в корзину целиком.
3. Корзина печатается ДАЖЕ когда таблица по задачам ПУСТА. Это не придирка к
   форматированию: пустая таблица — ровно то окно, где неатрибутированная
   работа наиболее вероятна, а прежний код в этом случае печатал «No usage
   data» и возвращался. Тогда это ложью не было только потому, что хук такие
   события выбрасывал раньше записи; после v48 стало бы.
"""

from __future__ import annotations

from pathlib import Path

from backend_queries_usage import usage_events_unattributed_rollup
from project_backend import SQLiteBackend
from project_service import ProjectService


def _make_service(tmp_path: Path) -> ProjectService:
    return ProjectService(SQLiteBackend(str(tmp_path / "tausik.db")))


def _append(svc: ProjectService, **kw):
    """usage_event_append с нулями по умолчанию — тесту важны только ключи."""
    params = {
        "session_id": None,
        "task_slug": None,
        "tokens_input": 10,
        "tokens_output": 5,
        "tokens_total": 15,
        "cost_usd": 0.001,
        "tool_calls": 1,
        "model_id": "claude-opus-4-7",
        "source": "posttool",
    }
    params.update(kw)
    return svc.be.usage_event_append(**params)


class TestBucketCounts:
    def test_event_without_task_or_session_is_counted(self, tmp_path):
        """Самый тихий случай: ни задачи, ни сессии. Он и есть предмет задачи."""
        svc = _make_service(tmp_path)
        _append(svc)
        bucket = usage_events_unattributed_rollup(svc.be)
        assert bucket["event_count"] == 1
        assert bucket["sessionless_events"] == 1
        assert bucket["tokens_total"] == 15

    def test_sessionless_is_broken_out_from_merely_taskless(self, tmp_path):
        """Два разных положения носят один и тот же NULL task_slug.

        Работа внутри сессии, но вне задачи — давно возможна. Работа без
        сессии вообще — то, что v48 сделала представимой впервые. Свести их в
        один безымянный итог значит потерять ровно то различие, ради которого
        миграция писалась.
        """
        svc = _make_service(tmp_path)
        svc.session_start()
        sess_id = int(svc.be.session_current()["id"])
        _append(svc, session_id=sess_id)  # в сессии, но вне задачи
        _append(svc)  # ни там, ни там
        bucket = usage_events_unattributed_rollup(svc.be)
        assert bucket["event_count"] == 2
        assert bucket["sessionless_events"] == 1

    def test_task_attributed_event_stays_out_of_the_bucket(self, tmp_path):
        svc = _make_service(tmp_path)
        svc.task_quick("t-bucket", "задача для FK")
        _append(svc, task_slug="t-bucket")
        assert usage_events_unattributed_rollup(svc.be)["event_count"] == 0

    def test_empty_when_nothing_is_unattributed(self, tmp_path):
        assert usage_events_unattributed_rollup(_make_service(tmp_path).be) == {
            "event_count": 0,
            "tokens_total": 0,
            "cost_usd": 0.0,
            "sessionless_events": 0,
        }


class TestBucketDoesNotDoubleCount:
    def test_session_record_mirror_row_is_excluded(self, tmp_path):
        """Зеркальная строка сессии несёт NULL task_slug — и потому опасна.

        `session_usage_record` пишет накопительную строку, равную СУММЕ
        posttool-строк той же сессии, всегда с NULL task_slug. Корзина,
        отобранная по одному только `task_slug IS NULL`, проглотила бы её и
        сообщила расход сессии вторично. Фильтр по source — не украшение.
        """
        svc = _make_service(tmp_path)
        svc.session_start()
        sess_id = int(svc.be.session_current()["id"])
        _append(svc, session_id=sess_id, source="session_record", tokens_total=9999, cost_usd=9.99)
        _append(svc, session_id=sess_id)  # настоящее событие вне задачи

        bucket = usage_events_unattributed_rollup(svc.be)
        assert bucket["event_count"] == 1, "зеркальная строка сессии попала в корзину"
        assert bucket["tokens_total"] == 15
        assert bucket["cost_usd"] < 1.0


class TestBucketIsPrinted:
    """Половина «строку видно». Считать и не печатать — тот же дроп, позже."""

    def _render(self, svc, capsys) -> str:
        from project_cli_metrics import _print_usage_cost_rollup

        _print_usage_cost_rollup(svc, None, None)
        return capsys.readouterr().out

    def test_printed_when_per_task_table_is_empty(self, tmp_path, capsys):
        """ГЛАВНОЕ утверждение файла: ранний возврат больше не прячет корзину."""
        svc = _make_service(tmp_path)
        _append(svc)
        out = self._render(svc, capsys)
        assert "No usage data" in out, "сообщение о пустой таблице по задачам осталось"
        assert "вне задачи: 1" in out, (
            "корзина не напечатана при пустой таблице по задачам — это и есть "
            "обмен тихого дропа на тихое сокрытие"
        )
        assert "вне сессии: 1" in out

    def test_printed_below_a_non_empty_table(self, tmp_path, capsys):
        svc = _make_service(tmp_path)
        svc.task_quick("t-shown", "задача для FK")
        _append(svc, task_slug="t-shown")
        _append(svc)
        out = self._render(svc, capsys)
        assert "t-shown" in out
        assert "вне задачи: 1" in out

    def test_silent_when_bucket_is_empty(self, tmp_path, capsys):
        """Постоянная строка «вне задачи: 0» — шум; скрывать при этом нечего."""
        svc = _make_service(tmp_path)
        svc.task_quick("t-only", "задача для FK")
        _append(svc, task_slug="t-only")
        assert "вне задачи" not in self._render(svc, capsys)
