"""Историческая порча цитат объявлена остатком; РОСТ по-прежнему HIGH.

ПОЧЕМУ НЕ ХРАПОВИК НА НУЛЕ. Журналы закрытий append-only: 51 плохая цитата лежит
внутри задач, закрытых давно, и переписать их значило бы подделать то самое
доказательство, ради честности которого проект существует. Историю нельзя
вычистить — но с седьмой смены #240 она и не растёт незаметно: `task done`
проверяет цитаты СВОЕЙ задачи, пока автор ещё может их поправить.

ПОЧЕМУ ЭТО ВООБЩЕ НАДО БЫЛО МЕНЯТЬ. Находка, которая повторяется на каждом
прогоне и с которой ничего нельзя сделать, не остаётся непрочитанной — она учит
пролистывать ВСЮ СВОЮ КАТЕГОРИЮ. Закрепление истории — это то, что оставляет
слову `high` значение.

ЧЕГО ЗДЕСЬ НЕТ: понижения строгости для НОВЫХ находок. Превышение остатка — по-
прежнему `high`, и это проверяется первым же тестом ниже.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import repo_coherence_collectors as rcc  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]


def _project(tmp_path: Path, baseline: dict | None) -> Path:
    (tmp_path / "tausik").mkdir(exist_ok=True)
    if baseline is not None:
        (tmp_path / "tausik" / "gates.json").write_text(
            json.dumps({"closure_evidence": {"baseline": baseline}}), encoding="utf-8"
        )
    return tmp_path


def _findings(monkeypatch, tmp_path: Path, counts: dict, baseline: dict | None):
    root = _project(tmp_path, baseline)

    class _FakeAudit:
        @staticmethod
        def audit_closure_evidence(_root, _tasks):
            return {"counts": counts, "findings": []}

    monkeypatch.setitem(sys.modules, "audit_closure_evidence", _FakeAudit)
    return rcc._rotted_evidence(root, [])


class TestРостОстаётсяHIGH:
    """Главный тест файла. Закрепление истории не смеет стать глушилкой."""

    def test_превышение_остатка_даёт_high(self, monkeypatch, tmp_path):
        found = _findings(
            monkeypatch,
            tmp_path,
            {"rotted": 35, "never_existed": 20},
            {"rotted": 31, "never_existed": 20},
        )
        high = [f for f in found if f.severity == "high"]
        assert len(high) == 1
        assert "ABOVE the declared remainder" in high[0].summary
        assert high[0].count == 4, "показан РОСТ, а не полное число"

    def test_отсутствие_остатка_читается_строго(self, monkeypatch, tmp_path):
        """Проект, ничего не объявивший, не получает поблажки: остаток нулевой,
        значит каждая находка есть рост. Это строгое прочтение и верное
        умолчание для того, кто ещё не выбирал."""
        found = _findings(monkeypatch, tmp_path, {"rotted": 1}, None)
        assert [f.severity for f in found] == ["high"]


class TestОстатокНеПрячется:
    """AC-5. Объявленный остаток обязан быть НАЗВАН, а не замолчан."""

    def test_совпадение_с_остатком_сообщается_как_остаток(self, monkeypatch, tmp_path):
        found = _findings(
            monkeypatch,
            tmp_path,
            {"rotted": 31, "never_existed": 20},
            {"rotted": 31, "never_existed": 20},
        )
        assert {f.severity for f in found} == {"low"}
        assert all("declared remainder" in f.summary for f in found)
        assert any("caught at closure since session #240" in f.detail for f in found)

    def test_ноль_находок_не_сообщается_вовсе(self, monkeypatch, tmp_path):
        assert (
            _findings(monkeypatch, tmp_path, {"rotted": 0, "never_existed": 0}, {"rotted": 31})
            == []
        )


class TestОстаткуРазрешеноТолькоУменьшАться:
    """AC-4. База выше правды — ложь в обратную сторону, и она тоже видна."""

    def test_остаток_выше_измеренного_просит_подтянуть(self, monkeypatch, tmp_path):
        found = _findings(monkeypatch, tmp_path, {"rotted": 20}, {"rotted": 31})
        assert len(found) == 1
        assert found[0].severity == "low"
        assert "tighten it" in found[0].summary
        assert "lie in the other direction" in found[0].detail


class TestЖивойОстатокЗакреплёнЧислом:
    """Замер на живом дереве, а не на фикстуре."""

    def test_база_объявлена_и_названа_числом(self):
        node = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
        baseline = node["closure_evidence"]["baseline"]
        assert isinstance(baseline["rotted"], int) and baseline["rotted"] > 0
        assert isinstance(baseline["never_existed"], int) and baseline["never_existed"] > 0

    def test_причина_записана_рядом_с_числом(self):
        """Число без объяснения через полгода читается как «кто-то смирился»."""
        node = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
        comment = node["closure_evidence"]["_comment"]
        assert "append-only" in comment
        assert "may only shrink" in comment

    @pytest.mark.parametrize("name", ["_rotted_evidence", "_closure_evidence_baseline"])
    def test_разрез_модуля_не_потерял_функций(self, name):
        """Коллекторы вынесены в свой модуль, когда `repo_coherence` перешёл
        500 строк. Публичное поведение линзы не менялось — проверяется тем, что
        обе функции на месте там, где их теперь ищут."""
        assert hasattr(rcc, name)
