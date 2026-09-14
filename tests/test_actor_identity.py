"""Разделение обязанностей становится проверяемым свойством квитанции.

ЗАМЕР, КОТОРЫЙ ЖЁСТЧЕ ПОСТАНОВКИ (смена #239). Квитанция verify подписывается
ключом ПРОЕКТА и отвечает, какие гейты прошли на каком состоянии кода. Кто делал
работу — не отвечает. При этом весь контроль качества стоит на разделении
обязанностей: внешний ревьюер на ДРУГОЙ модели, а с приходом P8 ещё и «автор
теста не есть исполнитель». Всё это объявлено и ничем не предъявлено.

Числа: 1686 квитанций, ни одна не несёт поля о деятеле. claimed_by пуст у ВСЕХ
1574 задач. Задач, где известны и стартовая, и закрывающая модель, — 29, и
модели РАЗНЫЕ ни в одной. То есть на пути verify разделения не просто не
засвидетельствовано — его там нет, и механизм обязан это ПОКАЗАТЬ.

ЧТО ЗАПИСЫВАЕТСЯ И ЧТО НЕТ. Квитанция записывает деятеля ПРОГОНА ПРОВЕРКИ. Она
НЕ говорит, кто писал тест, а кто код: это предмет P8 и в объём не входит.
Предъявить проверяемое поле как доказательство непроверяемого утверждения —
ровно тот класс, который весь релиз вычищается, поэтому граница здесь охраняется
тестом, а не обещанием.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import actor_identity as ai  # noqa: E402
import crypto_receipt as cr  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]


def _receipt(**actor):
    return cr.build_receipt(
        task_slug="t",
        git_sha=None,
        scope="manual",
        gates=[],
        passed=True,
        ran_at="2026-09-08T00:00:00Z",
        actor=ai.build_actor(**actor) if actor else None,
    )


class TestТриИсходаАНеДва:
    """AC-3 и AC-5. Квитанция без поля деятеля НЕ есть квитанция другого
    деятеля, и слить эти случаи значит выдать отсутствие данных за
    доказательство разделения."""

    @pytest.mark.parametrize(
        "second,expected",
        [
            pytest.param(
                {"session_id": 1, "model_id": "opus", "model_version": "5"},
                ai.SAME,
                id="same_session_same_model",
            ),
            pytest.param(
                {"session_id": 2, "model_id": "sonnet", "model_version": "5"},
                ai.DIFFERENT,
                id="other_session_other_model",
            ),
            pytest.param(
                {"session_id": 2, "model_id": "opus", "model_version": "5"},
                ai.DIFFERENT,
                id="other_session_same_model",
            ),
            pytest.param(
                {"session_id": 1, "model_id": "opus", "model_version": "6"},
                ai.DIFFERENT,
                id="same_session_other_model_version",
            ),
        ],
    )
    def test_вердикт_по_паре(self, second, expected):
        """Третий и четвёртый случаи важнее первых двух: одна модель в РАЗНЫХ
        сессиях — два прогона агентами, которые могли отличаться всем, чем
        прогон вообще может отличаться; а смена версии модели в одной сессии не
        должна проходить как «тот же деятель»."""
        first = _receipt(session_id=1, model_id="opus", model_version="5")
        assert ai.compare(first, _receipt(**second)) == expected

    def test_квитанция_без_деятеля_даёт_сказать_нельзя(self):
        """1686 существующих квитанций именно такие."""
        assert ai.compare(_receipt(), _receipt(session_id=1, model_id="opus")) == ai.UNKNOWN

    def test_обе_без_деятеля_тоже_сказать_нельзя(self):
        assert ai.compare(_receipt(), _receipt()) == ai.UNKNOWN

    def test_три_исхода_действительно_различаются(self):
        """Явно: проверка, дающая один ответ на всех входах, зелена по всем
        причинам сразу и не различает ни одной."""
        same = ai.compare(
            _receipt(session_id=1, model_id="o"), _receipt(session_id=1, model_id="o")
        )
        diff = ai.compare(
            _receipt(session_id=1, model_id="o"), _receipt(session_id=2, model_id="o")
        )
        unknown = ai.compare(_receipt(), _receipt())
        assert len({same, diff, unknown}) == 3


class TestОтсутствиеНеВыдаётсяЗаРазделение:
    """Единственная ошибка здесь, которая опаснее всех прочих."""

    def test_сказать_нельзя_не_равно_разные(self):
        assert ai.UNKNOWN != ai.DIFFERENT

    def test_вызывающий_обязан_требовать_разные_явно(self):
        """`!= SAME` засчитал бы КАЖДУЮ из 1686 старых квитанций как
        разделённую. Свойство проверяется на самом значении, а не на
        комментарии о нём."""
        verdict = ai.compare(_receipt(), _receipt())
        assert verdict != ai.SAME, "предпосылка"
        assert verdict is not ai.DIFFERENT, (
            "отсутствие данных прошло бы проверку вида '!= SAME' как разделение"
        )


class TestПустойБлокНеСчитаетсяДеятелем:
    """Тот же капкан, который `missing_v3_fields` документирует для рамок:
    присутствие судится по ЗНАЧЕНИЮ, а не по ключу."""

    def test_блок_из_пустых_полей_есть_отсутствие(self):
        assert ai.build_actor(session_id=None, model_id=None) is None

    def test_квитанция_с_пустым_блоком_даёт_сказать_нельзя(self):
        receipt = _receipt()
        receipt["actor"] = {"session_id": None, "model_id": None, "model_version": None}
        assert ai.actor_of(receipt) is None
        assert ai.compare(receipt, _receipt(session_id=1, model_id="o")) == ai.UNKNOWN

    @pytest.mark.parametrize("garbage", ["строка", 42, [], True])
    def test_мусор_вместо_блока_не_роняет_и_даёт_сказать_нельзя(self, garbage):
        receipt = _receipt()
        receipt["actor"] = garbage
        assert ai.actor_of(receipt) is None


class TestРольНеВходитВИдентичность:
    """Один агент, сменивший шляпу, — тот же агент. Считать смену роли сменой
    деятеля значит получить разделение обязанностей, которого нет."""

    def test_та_же_сессия_в_другой_роли_есть_тот_же_деятель(self):
        a = _receipt(session_id=1, model_id="o", model_version="5", role="developer")
        b = _receipt(session_id=1, model_id="o", model_version="5", role="reviewer")
        assert ai.compare(a, b) == ai.SAME

    def test_роль_всё_же_записана(self):
        """Она не идентичность, но она доказательство: под какой ролью работа
        объявлена, читается из подписанного документа."""
        assert _receipt(session_id=1, role="architect")["actor"]["role"] == "architect"


class TestПодписьПокрываетДеятеля:
    """AC-7. Поле, которое можно поменять, не сломав подпись, есть аннотация,
    а не свидетельство."""

    def test_правка_деятеля_меняет_канонические_байты(self):
        receipt = _receipt(session_id=1, model_id="opus", model_version="5")
        before = cr.canonical_bytes(receipt)
        receipt["actor"]["model_id"] = "другая-модель"
        assert cr.canonical_bytes(receipt) != before

    def test_добавление_деятеля_меняет_канонические_байты(self):
        assert cr.canonical_bytes(_receipt()) != cr.canonical_bytes(
            _receipt(session_id=1, model_id="o")
        )


class TestСтарыеКвитанцииОстаютсяВалидными:
    """AC-2. Поле ДОБАВЛЯЕТСЯ. Откат, обесценивающий 1686 закрытий, — не откат."""

    def test_отсутствие_деятеля_не_делает_квитанцию_неполной(self):
        """`missing_v3_fields` — то, чем проверка судит о полноте. Деятель
        намеренно не в этом списке."""
        receipt = _receipt()
        receipt.update(files=["a.py"], gate_signature="sig", expires_at="2030-01-01T00:00:00Z")
        assert cr.missing_v3_fields(receipt) == []

    def test_actor_не_попал_в_обязательные_поля(self):
        assert "actor" not in cr.V3_REQUIRED_FIELDS


class TestГраницаНазванаВКоде:
    """AC-4. Квитанция говорит о деятеле ПРОГОНА ПРОВЕРКИ и не говорит, кто
    писал тест, а кто код."""

    @staticmethod
    def _source() -> str:
        """Со схлопнутыми пробелами: утверждение живёт в ТЕКСТЕ, а перенос строки
        есть вёрстка. Первая редакция этого теста упала на переносе внутри фразы
        и проверяла бы вёрстку, а не сказанное."""
        text = (_REPO / "scripts" / "actor_identity.py").read_text(encoding="utf-8")
        return " ".join(text.split())

    def test_исходник_называет_границу(self):
        source = self._source()
        assert "does NOT say who wrote the test and who wrote the code" in source
        assert "P8" in source

    def test_исходник_называет_запрет_на_реестр_и_второй_ключ(self):
        """AC-6: ключи остаются локальными, деятель есть СОДЕРЖИМОЕ подписанной
        квитанции, а не второй подписант."""
        source = self._source()
        assert "NO IDENTITY REGISTRY AND NO CERTIFICATE AUTHORITY" in source
        assert "not a second signer" in source
