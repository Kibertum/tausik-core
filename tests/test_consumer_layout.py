"""Проверки, которые дома были зелёными, а у потребителя красными.

Дом против гостей: в этом репозитории `project_dir` и `lib_dir` — один каталог,
`scripts/` принадлежит харнессу, тесты лежат в `<root>/tests`. У потребителя
все три допущения ложны. Ни один существующий тест этого не проверял, и потому
шесть дефектов одного класса дожили до живых установок — последним нашёлся
защитный гейт memory-route, который у потребителя не находил себя и молча не
запускался.

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


def _sibling_predicate():
    """Предикат сопоставления процесса с проектом — вынесенный шов."""
    import importlib.util

    path = os.path.join(_REPO, "harness", "claude", "mcp", "project", "sibling_mcp.py")
    spec = importlib.util.spec_from_file_location("_sibling_mcp_for_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._command_belongs_to_project


def test_a_relative_launch_is_recognised_as_ours():
    """Сервер, запущенный ОТНОСИТЕЛЬНЫМ путём, обязан считаться нашим.

    Было: сопоставление требовало абсолютного пути проекта в чужой командной
    строке, а серверы запускаются как
    `python ./.claude/mcp/project/server.py --project .`. Условие не
    выполнялось никогда — замер на живой машине дал десять работающих
    процессов и счётчик «соседей 0». Ноль, означающий «не умею считать»,
    неотличим от нуля, означающего «соседей нет».

    Стало: рабочий каталог процесса тоже считается признаком, и он передаётся
    предикату аргументом — поэтому относительный случай проверяется здесь, а не
    остаётся заявленным.
    """
    belongs = _sibling_predicate()
    needle = "mcp/project/server.py"
    project = os.path.normpath("/home/dev/proj")

    absolute = f"python {project}/.claude/mcp/project/server.py --project {project}"
    assert belongs(absolute, project, needle), "абсолютный запуск обязан распознаваться"

    relative = "python ./.claude/mcp/project/server.py --project ."
    assert not belongs(relative, project, needle), (
        "без рабочего каталога относительный запуск распознать НЕЧЕМ — "
        "и предикат обязан честно об этом говорить, а не угадывать"
    )
    assert belongs(relative, project, needle, cwd=project), (
        "с известным рабочим каталогом относительный запуск обязан распознаваться — "
        "это и есть случай, ради которого правка делалась"
    )


def test_an_unknown_working_directory_is_not_a_guess():
    """Неизвестный рабочий каталог не засчитывается за совпадение.

    Догадка вместо измерения дала бы тот же бесполезный счётчик, только с
    другой стороны: вместо вечного нуля — вечное завышение.
    """
    belongs = _sibling_predicate()
    needle = "mcp/project/server.py"
    project = os.path.normpath("/home/dev/proj")
    relative = "python ./.claude/mcp/project/server.py --project ."

    assert not belongs(relative, project, needle, cwd=None)
    assert not belongs(relative, project, needle, cwd=os.path.normpath("/home/dev/other"))


def test_a_foreign_project_is_not_counted_as_a_sibling():
    """Точность важнее полноты: чужой проект соседом не считается.

    Лечение, которое считает соседями всех, хуже болезни: счётчик перестанет
    означать что-либо, а лишний «сосед» читается как утечка процессов.
    """
    belongs = _sibling_predicate()
    needle = "mcp/project/server.py"
    ours = os.path.normpath("/home/dev/proj")
    theirs = os.path.normpath("/home/dev/other")

    foreign = f"python {theirs}/.claude/mcp/project/server.py --project {theirs}"
    assert not belongs(foreign, ours, needle), "чужой проект не наш сосед"


def test_an_unrelated_process_is_never_a_sibling():
    """Процесс без нашего серверного модуля не наш ни при каких путях."""
    belongs = _sibling_predicate()
    needle = "mcp/project/server.py"
    project = os.path.normpath("/home/dev/proj")

    assert not belongs(f"python {project}/manage.py runserver", project, needle)
    assert not belongs("", project, needle)


# --- дефект 5: защитный гейт в pre-commit -----------------------------------


def _find_engine_file(project_root: str, rel: str) -> str:
    """Прогнать РЕАЛЬНУЮ функцию разрешения из `scripts/hooks/pre-commit`.

    Читается живой файл хука, а не переписанная копия правила: копия разошлась
    бы с оригиналом ровно тогда, когда оригинал сломают.
    """
    import subprocess

    hook = os.path.join(_REPO, "scripts", "hooks", "pre-commit")
    with open(hook, encoding="utf-8") as fh:
        body = fh.read()
    # Берём ТОЛЬКО текст функции: запустить хук целиком значило бы прогнать
    # mypy и переиндексацию RAG ради одной строки ответа.
    start = body.index("find_engine_file() {")
    end = body.index("\n}\n", start) + 3
    script = body[start:end] + f'\nfind_engine_file "{rel}" || true\n'

    # ФАЙЛОМ, а не через `bash -c`: при `-c` позиционные параметры функции
    # приходят пустыми, `$1` внутри неё разворачивается в пустую строку, и
    # проверка отвечала бы «не найдено» независимо от раскладки — то есть
    # краснела бы на способе запуска, а не на дефекте. Git запускает хук
    # файлом, и проверка запускает так же.
    # Скрипт кладётся ВНУТРЬ проверяемого дерева и запускается относительным
    # именем: Git Bash на Windows принимает абсолютный путь вида `C:\\...`
    # не всегда, и молча возвращал бы пустой ответ — снова красный тест по
    # причине, не имеющей отношения к дефекту.
    path = os.path.join(project_root, "_find_engine_file_probe.sh")
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(script)
        try:
            out = subprocess.run(
                ["bash", "./_find_engine_file_probe.sh"],
                cwd=project_root,
                capture_output=True,
                text=True,
                # Кодировка называется ЯВНО: без неё вывод дочернего процесса
                # читается кодировкой родителя, и результат теста зависел бы от
                # флагов запуска pytest. Поймано собственным храповиком
                # tests/test_hook_encoding.py, а не глазами.
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except (FileNotFoundError, OSError):
            import pytest

            pytest.skip("bash недоступен на этом хосте")
    finally:
        os.unlink(path)
    assert out.returncode == 0, f"запуск не состоялся: rc={out.returncode} stderr={out.stderr!r}"
    return out.stdout.strip()


def test_the_memory_route_gate_is_reachable_in_a_plain_clone(tmp_path):
    """Защитный гейт обязан НАЙТИСЬ у потребителя.

    Было: хук искал `scripts/gate_memory_route.py` и
    `.tausik-lib/scripts/gate_memory_route.py`. У потребителя первый принадлежит
    ПРОЕКТУ и гейта не содержит, второй пуст при клоне без
    `--recurse-submodules`. Развёрнутая копия в профиле IDE не пробовалась
    вовсе. `MEMORY_ROUTE_GATE` оставался пустым, блок пропускался, и весь
    контроль молча не выполнялся — при том что docs/en/security.md обещает
    применение deny-list'а «IDE-agnostically over the working tree».
    """
    p = build_consumer_project(tmp_path)

    found = _find_engine_file(p.root, "scripts/gate_memory_route.py")

    assert found, "гейт не найден: контроль молча не запустится"
    assert os.path.isfile(os.path.join(p.root, found)), f"найден несуществующий путь: {found}"
    assert ".claude" in found.replace("\\", "/"), (
        f"ожидалась развёрнутая копия профиля, найдено {found!r}"
    )


def test_the_search_does_not_step_into_the_parent_directory(tmp_path):
    """НЕГАТИВНЫЙ: поиск не выходит за пределы проекта.

    Глоб `.*/` раскрывается и в `..`, и тогда поиск ушёл бы в РОДИТЕЛЬСКИЙ
    каталог — чужое дерево. Кладём приманку рядом с проектом и проверяем, что
    она не подобрана.
    """
    p = build_consumer_project(tmp_path)
    bait = tmp_path / "scripts"
    bait.mkdir()
    (bait / "gate_memory_route.py").write_text("# чужой гейт\n", encoding="utf-8")

    found = _find_engine_file(p.root, "scripts/gate_memory_route.py")

    assert ".." not in found, f"поиск шагнул наверх: {found!r}"
    assert os.path.realpath(os.path.join(p.root, found)) != os.path.realpath(
        str(bait / "gate_memory_route.py")
    ), "подобран гейт из чужого дерева"


def test_the_engines_own_repo_prefers_its_source_over_the_deployed_copy():
    """НЕГАТИВНЫЙ: в репозитории движка побеждает ИСХОДНИК, а не развёрнутая копия.

    Развёрнутый профиль здесь отстаёт от каждой правки, и коммит проверялся бы
    вчерашним гейтом. Имена этих файлов принадлежат движку, поэтому наличие
    `scripts/gate_memory_route.py` и означает «это его собственный репозиторий».
    """
    found = _find_engine_file(_REPO, "scripts/gate_memory_route.py")

    assert found == "scripts/gate_memory_route.py", (
        f"в репозитории движка выбран не исходник, а {found!r}"
    )


def _run_gate_prologue(project_root: str) -> tuple[int, str]:
    """Выполнить ПРОЛОГ хука — до mypy — и вернуть (код, stderr).

    Берётся кусок живого файла от разрешения интерпретатора до строки запуска
    mypy: сам mypy тут не нужен и стоил бы полминуты на каждый тест, а
    проверяемое поведение целиком лежит выше него.
    """
    import subprocess

    hook = os.path.join(_REPO, "scripts", "hooks", "pre-commit")
    with open(hook, encoding="utf-8") as fh:
        body = fh.read()
    start = body.index("# --- Python interpreter")
    end = body.index('echo "Running mypy type check..."')
    path = os.path.join(project_root, "_gate_prologue_probe.sh")
    # Интерпретатор называется ЯВНО. Догадки хука (`.tausik/venv/...`, затем
    # голое `python`) на этом хосте не срабатывают: в Git Bash под Windows
    # `python` в PATH нет вовсе. Без переопределения проверка краснела бы на
    # отсутствии интерпретатора, а не на поведении гейта — и заодно скрывала бы,
    # что у хука до сих пор не было способа сказать ему, где Python.
    #
    # Переменная пишется В САМ СКРИПТ, а не передаётся через `env=`: Git Bash в
    # этой связке не получает окружение, заданное подпроцессу, и проверка молча
    # шла бы по ветке догадок. Ветка хука `${TAUSIK_PYTHON:-}` при этом
    # исполняется ровно та же.
    # Прямые слэши обязательны: Git Bash отказывается выполнять `C:\\Python311\\
    # python.exe` со словами «command not found», и всякая проверка, которой
    # нужен Python, тихо деградирует. Это же записано в самом хуке.
    interpreter = sys.executable.replace("\\", "/")
    prologue = f"export TAUSIK_PYTHON='{interpreter}'\n" + body[start:end]
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(prologue)
        try:
            out = subprocess.run(
                ["bash", "./_gate_prologue_probe.sh"],
                cwd=project_root,
                capture_output=True,
                text=True,
                # Кодировка называется ЯВНО: без неё вывод дочернего процесса
                # читается кодировкой родителя, и результат теста зависел бы от
                # флагов запуска pytest. Поймано собственным храповиком
                # tests/test_hook_encoding.py, а не глазами.
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
        except (FileNotFoundError, OSError):
            import pytest

            pytest.skip("bash недоступен на этом хосте")
    finally:
        os.unlink(path)
    return out.returncode, out.stderr


def test_a_gate_that_cannot_find_itself_says_so(tmp_path):
    """НЕ НАЙДЕН — значит СКАЗАНО.

    Молчание и было тем, что позволило контролю исчезнуть: проверка, не
    нашедшая себя, не имеет права выглядеть так же, как прошедшая. Предыдущая
    редакция объявляла молчаливую инертность допустимой прямо в комментарии
    («Inert when scripts/ is absent»).

    Предупреждение, а не блокировка: блокировать значило бы выдумать новый
    отказ для проектов, у которых движка никогда и не было.
    """
    p = build_consumer_project(tmp_path)
    os.remove(os.path.join(p.deployed_scripts, "gate_memory_route.py"))

    rc, stderr = _run_gate_prologue(p.root)

    assert rc == 0, "отсутствие гейта не должно ронять коммит"
    assert "memory-route gate not found" in stderr, f"молчание вместо отказа: {stderr!r}"


def test_a_gate_switched_off_by_decision_stays_quiet(tmp_path):
    """НЕГАТИВНЫЙ: «выключен решением» и «пропал случайно» — разные состояния.

    Проект, сознательно погасивший гейт, не должен получать предупреждение о
    нём на каждый коммит: шум, который нельзя убрать, перестают читать, и
    вместе с ним перестают читать настоящие предупреждения.
    """
    p = build_consumer_project(tmp_path)
    os.remove(os.path.join(p.deployed_scripts, "gate_memory_route.py"))
    cfg_dir = os.path.join(p.root, ".tausik")
    os.makedirs(cfg_dir, exist_ok=True)
    with open(os.path.join(cfg_dir, "config.json"), "w", encoding="utf-8") as fh:
        fh.write('{"gates": {"memory_route": {"enabled": false}}}')

    rc, stderr = _run_gate_prologue(p.root)

    assert rc == 0
    assert "memory-route gate not found" not in stderr, (
        f"шумит о гейте, который выключен намеренно: {stderr!r}"
    )


# --- шестой дефект: копии правила «где библиотека» ---------------------------


def test_claudemd_drift_asks_the_shared_resolver_for_the_library(tmp_path, monkeypatch):
    """Дрейф CLAUDE.md спрашивает источник у `library_source`, а не считает сам.

    `scripts_drift_names` свели к общей функции — а `claudemd_drift_report` в
    том же файле осталась со своим вычислением, и приоритет там был ОБРАТНЫЙ:
    два `sys.path.insert(0, …)` подряд, из которых второй, путь проекта,
    оказывался первым в списке. Проверки `isdir` не было вовсе.

    Проверяется ВЫЗОВ, а не результат, и это осознанно. Результат обеих
    редакций на потребительской фикстуре совпадает — библиотека пуста, шаблона
    нет ни там, ни тут, обе возвращают `None`. Тест на результат был бы зелёным
    и до починки, то есть не проверял бы ничего (конвенция #365: извлечение
    ради общей функции обязано добавить проверку на ВЫЗЫВАЮЩЕГО).
    """
    import service_doctor_drift

    p = build_consumer_project(tmp_path)
    with open(os.path.join(p.root, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write("# CLAUDE.md\n\nтело\n")

    asked = []
    real = service_doctor_drift.library_source

    def spy(project_dir, subdir):
        asked.append(subdir)
        return real(project_dir, subdir)

    monkeypatch.setattr(service_doctor_drift, "library_source", spy)
    service_doctor_drift.claudemd_drift_report(p.root)

    assert "bootstrap" in asked, (
        "источник шаблонов вычисляется на месте, а не спрашивается у общей функции — "
        f"спрошено: {asked}"
    )
