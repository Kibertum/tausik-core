"""Новый проект обязан суметь закрыть ПЕРВУЮ задачу.

НАЙДЕНО СКВОЗНЫМ ПРОГОНОМ, а не чтением кода (смена #240). Чистый проект: git
init, две функции, один тест. Развернул TAUSIK, завёл задачу, написал код,
verify ЗЕЛЁНЫЙ — и `task done` ЗАБЛОКИРОВАН двумя гейтами разом:

    test_dedupe           храповик не читается из tausik/gates.json
    claudemd_state_drift  DYNAMIC-блок без хвоста памяти

Оба включены по умолчанию и оба severity=block. То есть новый пользователь не мог
закрыть ни одной задачи, пока не догадается создать храповик руками или выключить
гейты; ни то, ни другое нигде не сказано.

ПОЧЕМУ ЭТОГО НЕ ВИДЕЛИ ГОДАМИ. Оба гейта зелены на НАШЕМ дереве: у нас есть и
`gates.json` с базой храповика, и отрисованный блок. Гейт, работающий у автора и
отказывающий у пользователя, — тот же класс, ради которого заведён
`cross_model_parity`, только по другой оси: не хост, а ВОЗРАСТ ПРОЕКТА.

ПОЧЕМУ ЭТОТ ТЕСТ ПОДНИМАЕТ НАСТОЯЩИЙ ПРОЕКТ, А НЕ ФИКСТУРУ. Дефект был именно в
том, чего фикстура не воспроизводит: в отсутствии файлов, которые у нас есть по
историческим причинам. Проверять его на подготовленном каталоге значило бы
готовить ровно то, чьё отсутствие и есть предмет.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

CROSSCUTTING_SCOPE = ["scripts/", "bootstrap/"]

pytestmark = pytest.mark.slow

_CALC = "def add(a, b):\n    return a + b\n\n\ndef subtract(a, b):\n    return a - b\n"
_TEST = (
    "from src.calc import add, subtract\n\n\n"
    "def test_add():\n    assert add(2, 2) == 4\n\n\n"
    "def test_subtract():\n    assert subtract(2, 2) == 0\n    assert subtract(2, 2) != 4\n"
)


def _run(argv: list[str], cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env={**os.environ, "PYTHONUTF8": "1"},
    )


@pytest.fixture(scope="module")
def consumer(tmp_path_factory) -> Path:
    """Настоящий чужой проект, поднятый настоящим bootstrap."""
    root = tmp_path_factory.mktemp("consumer")
    (root / "src").mkdir()
    (root / "src" / "calc.py").write_text(_CALC, encoding="utf-8")
    (root / "test_calc.py").write_text(_TEST, encoding="utf-8")
    _run(["git", "init", "-q", "."], root)
    _run(["git", "add", "-A"], root)
    _run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        root,
    )
    result = _run(
        [
            sys.executable,
            str(_REPO / "bootstrap" / "bootstrap.py"),
            "--project-dir",
            str(root),
            "--lib-dir",
            str(_REPO),
            "--init",
            "calc",
            "--ide",
            "claude",
        ],
        root,
    )
    assert result.returncode == 0, f"bootstrap упал: {result.stdout[-800:]}"
    return root


def _wrapper(root: Path) -> str:
    name = "tausik.cmd" if sys.platform == "win32" else "tausik"
    return str(root / ".tausik" / name)


class TestНовыйПроектЗакрываетПервуюЗадачу:
    """AC-1 и AC-5. Сквозной путь, а не проверка отдельных гейтов."""

    def test_путь_целиком_проходит(self, consumer):
        wrapper = _wrapper(consumer)
        assert (
            _run(
                [
                    wrapper,
                    "task",
                    "quick",
                    "add subtract",
                    "--goal",
                    "смоук",
                    "--ac",
                    "AC-1 функция есть. AC-2 НЕГАТИВ: subtract(2,2) не равно 4.",
                    "--role",
                    "developer",
                    "--stack",
                    "python",
                ],
                consumer,
            ).returncode
            == 0
        )
        _run(
            [
                wrapper,
                "task",
                "update",
                "add-subtract",
                "--scope-paths",
                "src/calc.py",
                "test_calc.py",
            ],
            consumer,
        )
        _run([wrapper, "task", "start", "add-subtract"], consumer)

        verify = _run(
            [
                wrapper,
                "verify",
                "--task",
                "add-subtract",
                "--relevant-files",
                "src/calc.py",
                "test_calc.py",
            ],
            consumer,
        )
        assert "[PASS] pytest" in verify.stdout, verify.stdout[-800:]

        # ОДНОСТРОЧНЫЕ записи, по одной на критерий. Многострочный аргумент
        # через `.cmd`-обёртку на Windows отвергается её же защитой командной
        # строки — это не дефект, а именованный отказ с указанным средством
        # (POSIX-обёртка из bash либо MCP). Тест идёт путём, работающим на
        # обеих платформах.
        for line in (
            "AC-1: ✓ test_calc.py::test_subtract",
            "AC-2: ✓ test_calc.py::test_subtract",
        ):
            logged = _run([wrapper, "task", "log", "add-subtract", line], consumer)
            assert logged.returncode == 0, (
                "запись доказательства отвергнута — дальше проверялся бы не тот "
                f"отказ: {(logged.stdout or '')[-400:]}"
            )
        done = _run([wrapper, "task", "done", "add-subtract", "--ac-verified"], consumer)

        assert done.returncode == 0, (
            "новый проект не может закрыть первую задачу:\n"
            + (done.stdout or "")[-1200:]
            + (done.stderr or "")[-400:]
        )
        assert "completed" in done.stdout

    def test_блок_состояния_отрисован_bootstrap_ом(self, consumer):
        """Корень одного из двух блоков: `init` писал ПУСТОЙ динамический блок,
        а гейт дрейфа читает его отсутствие как дрейф."""
        text = (consumer / "CLAUDE.md").read_text(encoding="utf-8")
        # Проверяется то, что блок РИСУЕТ в пустом проекте — строки состояния.
        # Прежняя проверка искала «Memory tail»: этот заголовок появляется только
        # у непустого хвоста, а непустым его на машине автора делала ОБЩАЯ база
        # знаний (~/.tausik-knowledge), которой в CI нет — тест утверждал
        # артефакт машины, и опубликованная лента была красной (#7719).
        assert "## Current State" in text, "bootstrap не отрисовал динамический блок"
        assert "Tasks: 0/0 done" in text, "блок состояния не про этот (пустой) проект"


class TestГейтыОтличаютОТСУТСТВИЕОтНАРУШЕНИЯ:
    """AC-2 и AC-3. Починка ложного блока не смеет стать дырой."""

    def test_нет_храповика_не_есть_нарушение(self, tmp_path):
        import gate_test_dedupe as gate

        assert gate.ratchet_file_exists(str(tmp_path)) is False

    def test_на_нашем_дереве_храповик_есть_и_читается(self):
        import gate_test_dedupe as gate

        assert gate.ratchet_file_exists(str(_REPO)) is True
        baseline = gate.load_baseline(str(_REPO))
        assert baseline is not None and baseline["groups"] > 0, (
            "храповик перестал читаться здесь — тогда предыдущий тест зелен по "
            "другой причине, и различие ОТСУТСТВИЕ/НАРУШЕНИЕ не проверено"
        )

    def test_испорченный_храповик_по_прежнему_отказ(self, tmp_path):
        """Граница: файл ЕСТЬ и не читается — это НАРУШЕНИЕ, а не отсутствие.
        Смешать их значило бы превратить испорченный храповик в зелёный
        вердикт о тестах."""
        import gate_test_dedupe as gate

        (tmp_path / "tausik").mkdir()
        (tmp_path / "tausik" / "gates.json").write_text(
            '{"test_dedupe": "мусор"}', encoding="utf-8"
        )
        assert gate.ratchet_file_exists(str(tmp_path)) is True
        assert gate.load_baseline(str(tmp_path)) is None
