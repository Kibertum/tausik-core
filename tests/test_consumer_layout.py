"""Проверки, которые дома были зелёными, а у потребителя красными.

Дом против гостей: в этом репозитории `project_dir` и `lib_dir` — один каталог,
`scripts/` принадлежит харнессу, тесты лежат в `<root>/tests`. У потребителя
все три допущения ложны. Ни один существующий тест этого не проверял, и потому
четыре дефекта одного класса дожили до живых установок.

Каждый тест ниже утверждает ПРАВИЛЬНОЕ поведение. Заводились они с пометками
`pytest.mark.xfail(strict=True)`, потому что на момент заведения три из четырёх
дефектов были живыми. Пометки сняты по мере починки, и снимала их не память
автора, а сам храповик: как только дефект исправлен, ожидаемое падение
становится XPASS и валит прогон. Фикстура не может тихо разойтись с состоянием
кода ни в одну сторону — ни пропустив починку, ни продолжив утверждать дефект.

Приём описан паттерном #388; при добавлении сюда нового живого дефекта пометка
возвращается вместе с ним.
"""

from __future__ import annotations

import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))
sys.path.insert(0, os.path.join(_REPO, "bootstrap"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consumer_layout import build_consumer_project  # noqa: E402


# --- сама фикстура обязана быть реалистичной --------------------------------


def test_the_fixture_reproduces_what_a_plain_clone_looks_like(tmp_path):
    """Если фикстура нереалистична, всё остальное в этом файле ничего не стоит."""
    p = build_consumer_project(tmp_path)

    lib_hooks = os.path.join(p.lib, "scripts", "hooks")
    assert os.path.isdir(lib_hooks), "каталог сабмодуля должен существовать"
    assert not os.listdir(lib_hooks), (
        "библиотека обязана быть ПУСТОЙ — так выглядит клон без --recurse-submodules"
    )
    assert os.listdir(p.deployed_hooks), "развёрнутые хуки обязаны быть на месте"
    assert os.path.isdir(p.own_scripts), "у проекта есть СВОИ scripts/"
    assert not os.path.isdir(os.path.join(p.root, "tests")), (
        "тесты НЕ в <root>/tests — иначе раскладка не потребительская"
    )
    assert os.path.isdir(p.tests_dir)


# --- дефект 1: хуки. Исправлен — служит контролем ---------------------------


def test_hooks_are_reachable_in_a_plain_clone(tmp_path):
    """Контроль: этот дефект уже исправлен, и фикстура обязана это подтверждать.

    Зелёный здесь доказывает, что фикстура не красит всё подряд.
    """
    from bootstrap_generate import generate_settings_claude

    p = build_consumer_project(tmp_path)
    generate_settings_claude(p.ide_dir, p.root)

    import json

    settings = json.loads(open(os.path.join(p.ide_dir, "settings.json"), encoding="utf-8").read())
    commands = [
        h["command"]
        for entries in settings["hooks"].values()
        for entry in entries
        for h in entry["hooks"]
    ]
    assert commands

    missing = []
    for command in commands:
        script = next(t for t in command.split() if t.endswith(".py"))
        resolved = script.replace("${CLAUDE_PROJECT_DIR}", p.root)
        if not os.path.isabs(resolved):
            resolved = os.path.join(p.root, resolved)
        if not os.path.isfile(resolved):
            missing.append(resolved)
    assert not missing, f"{len(missing)} из {len(commands)} хуков недостижимы"


# --- дефект 2: гейт pytest ---------------------------------------------------


def test_the_pytest_gate_finds_tests_that_are_not_at_root(tmp_path):
    """Блокирующий гейт обязан НАЙТИ тесты, где бы они ни лежали.

    Было: `<base>/tests` захардкожен в трёх местах, `build_tests_index`
    возвращал пустой словарь, `run_command_gate` попадал в ветку «нет
    замапленных тестов» и отдавал SKIP — неотличимый от честного «изменение
    не мапится ни на один тест». Блокирующий гейт был включён и не проверял
    ничего.

    Стало: корни обнаруживаются. Явная настройка `testing.roots` побеждает;
    при её отсутствии работает ограниченный поиск на два уровня вглубь, мимо
    вендоренных и служебных каталогов. Пометка xfail снята после того, как
    strict-храповик поймал починку XPASS'ом.
    """
    from gate_test_resolver import build_tests_index

    p = build_consumer_project(tmp_path)
    index = build_tests_index(p.root)

    assert index, "индекс тестов пуст: гейт не увидит ни одного теста и вырождается в no-op"
    assert any("quota" in key for key in index), (
        f"тест test_quota.py не попал в индекс; ключи: {sorted(index)[:5]}"
    )


# --- дефект 3: doctor drift --------------------------------------------------


def test_drift_does_not_accuse_the_projects_own_scripts(tmp_path):
    """Собственные скрипты проекта — не дрейф харнесса.

    Было: копировщик разворачивает из `<lib>/scripts`, а проверка читала
    `<project>/scripts`. Дома это один каталог; у потребителя — два разных, и
    doctor рапортовал дрейф на `deploy.sh`, которого в харнессе нет и не было.
    Лечения у того предупреждения не существовало: сколько ни запускай
    bootstrap, чужие файлы в профиль не приедут. Хуже ложной тревоги была
    слепота — те ~300 файлов, что реально разворачиваются из `.tausik-lib`,
    не сравнивались вовсе.

    Стало: источник разрешает общая функция `library_source`, библиотека
    побеждает. К ней же сведён и одноимённый гейт, у которого было своё
    вычисление с обратным порядком, — вместо третьей копии правила их стало
    на одну меньше. Пометка xfail снята после того, как strict-храповик
    поймал починку XPASS'ом.
    """
    from service_doctor_drift import scripts_drift_names

    p = build_consumer_project(tmp_path)
    drift = scripts_drift_names(p.root) or []

    accused = [name for name in drift if any(own in name for own in ("deploy.sh", "pg_backup.sh"))]
    assert not accused, (
        f"doctor обвиняет собственные скрипты проекта: {accused}. "
        "Это вечное предупреждение, которое нечем вылечить."
    )


# --- дефект 4: детектор соседей ---------------------------------------------


def test_sibling_detector_has_no_seam_to_test_yet():
    """Отсутствие проверки названо вслух, а не выдано за её прохождение.

    Сопоставление процесса с проектом вкраплено в `_enumerate_sibling_mcps` и
    отдельным предикатом не вынесено, поэтому проверить его на фикстуре нельзя
    без поднятия процессов. Шов выносится задачей
    sibling-mcp-detector-is-blind-to-a-relative-launch-path; тогда сюда
    добавляется проверка, и этот тест заменяется на неё.
    """
    self_check = os.path.join(_REPO, "harness", "claude", "mcp", "project", "self_check.py")
    source = open(self_check, encoding="utf-8").read()
    assert "_enumerate_sibling_mcps" in source
    assert "def _command_belongs_to_project" not in source, (
        "предикат вынесен — значит шов появился, и этот тест пора заменить "
        "настоящей проверкой на фикстуре"
    )
