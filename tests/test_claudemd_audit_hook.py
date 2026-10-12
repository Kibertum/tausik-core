"""Регрессия аудит-хука tests/tools/claudemd_audit/sitecustomize.py.

Хук — инструмент, а не контроль: он ничего не блокирует и ничего не чинит. Но
инструмент, которому верят при поиске виновника, обязан быть проверен на ОБЕ
стороны: он должен ловить запись и должен МОЛЧАТЬ на всём остальном. Хук,
пишущий на каждое чтение, утопит настоящее событие в шуме ровно тогда, когда
понадобится, — поэтому молчание проверяется наравне с поимкой.

ЦЕЛЬ ВСЕГДА ВРЕМЕННАЯ. Ни один тест здесь не трогает настоящие корневые
CLAUDE.md/AGENTS.md: тест, утверждающий что-то про запись в них, при провале
испортил бы ровно те файлы, о которых утверждает, — а под `-n auto` ещё и на
глазах у всех воркеров. Роль корня играет tmp_path.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_DIR = REPO_ROOT / "tests" / "tools" / "claudemd_audit"

# Кросс-режущий: тест гоняет хук ПОДПРОЦЕССОМ (см. `_run` ниже) и потому не
# импортирует ни одной его строки. Импортное ребро резолвера сюда не дотягивается,
# а имя файла не совпадает с именем охраняемого модуля — значит без этого
# объявления изменение самого хука НЕ выбирает его собственный тест.
# Замерено в #193: до объявления resolve_test_files_for_relevant([<хук>]) не
# возвращал этот файл, и полная лента краснела на храповике видимости
# (test_crosscutting_registry::TestInvisibleToEveryEdge) две смены подряд, потому
# что обе закрывались scoped-прогоном, для которого общедеревянный храповик
# невидим (конвенция #421).
# Объявлено ОХРАНЯЕМОЕ ДЕРЕВО, а не пустой опт-аут: пустой список сказал бы
# «просмотрено, не кросс-режущий», что неверно — у этого теста есть ровно один
# файл, изменение которого обязано его запускать.
CROSSCUTTING_SCOPE = ["tests/tools/claudemd_audit/"]


def _run(code: str, tmp_path: Path, *, arm: bool = True, worker: str | None = None) -> list[dict]:
    """Запустить подпроцесс python с хуком НА PYTHONPATH и вернуть ленту событий.

    `arm=False` оставляет хук на пути, но НЕ задаёт переменные окружения: это и
    есть проверка того, что выключенный хук выключен, а не «поставлен и молчит».
    """
    log = tmp_path / "audit.jsonl"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(HOOK_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("PYTEST_XDIST_WORKER", None)
    if worker is not None:
        env["PYTEST_XDIST_WORKER"] = worker
    if arm:
        env["CLAUDEMD_AUDIT_ROOT"] = str(tmp_path)
        env["CLAUDEMD_AUDIT_LOG"] = str(log)
    else:
        env.pop("CLAUDEMD_AUDIT_ROOT", None)
        env.pop("CLAUDEMD_AUDIT_LOG", None)

    proc = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == 0, f"подпроцесс упал: {proc.stderr}"
    if not log.exists():
        return []
    return [
        json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


WRITE_TARGET = "import pathlib\npathlib.Path('CLAUDE.md').write_text('x', encoding='utf-8')\n"


# --- AC1: имя sitecustomize не лежит там, где интерпретатор возьмёт его сам ---


def test_no_sitecustomize_at_repo_root() -> None:
    """Корневой sitecustomize.py затенил бы системный для КАЖДОГО процесса.

    Ради этого хук и вынесен в отдельный каталог; проверка держит решение, а не
    полагается на то, что его помнят.
    """
    assert not (REPO_ROOT / "sitecustomize.py").exists()


def test_hook_lives_in_its_own_directory() -> None:
    assert (HOOK_DIR / "sitecustomize.py").is_file()
    # В каталоге не должно заводиться ничего исполняемого сверх самого хука:
    # он попадает на PYTHONPATH целиком, и всякий модуль рядом станет видимым
    # импортом для любого процесса, которому хук взвели.
    others = sorted(p.name for p in HOOK_DIR.glob("*.py") if p.name != "sitecustomize.py")
    assert others == [], f"лишние модули в каталоге хука: {others}"


# --- AC3: ловит запись, и в событии есть чем назвать автора ------------------


def test_records_a_write_to_the_target(tmp_path: Path) -> None:
    events = _run(WRITE_TARGET, tmp_path)
    assert len(events) == 1, f"ожидалось одно событие, получено {len(events)}"
    ev = events[0]
    assert "w" in str(ev["mode"])
    assert ev["pid"] > 0
    assert ev["stack"], "событие без стека не называет автора — ради стека хук и существует"
    assert any("CLAUDE.md" in frame or "write_text" in frame for frame in ev["stack"])


def test_records_agents_md_too(tmp_path: Path) -> None:
    events = _run(
        "import pathlib\npathlib.Path('AGENTS.md').write_text('x', encoding='utf-8')\n",
        tmp_path,
    )
    assert len(events) == 1
    assert events[0]["path"].endswith("AGENTS.md")


def test_worker_label_comes_from_xdist_env(tmp_path: Path) -> None:
    """Имя воркера — то единственное, что отличает 19 подозреваемых друг от друга."""
    events = _run(WRITE_TARGET, tmp_path, worker="gw17")
    assert events[0]["worker"] == "gw17"


def test_worker_is_main_outside_xdist(tmp_path: Path) -> None:
    events = _run(WRITE_TARGET, tmp_path)
    assert events[0]["worker"] == "main"


# --- AC4: негативные сценарии, оба ------------------------------------------


def test_silent_on_read(tmp_path: Path) -> None:
    """Чтение цели событий НЕ порождает.

    Это не придирка к объёму ленты: CLAUDE.md читается на каждом старте сессии и
    в куче тестов. Хук, пишущий на чтение, даёт ленту, в которой единственная
    настоящая запись неотличима от фона.
    """
    (tmp_path / "CLAUDE.md").write_text("already here", encoding="utf-8")
    events = _run(
        "import pathlib\nassert pathlib.Path('CLAUDE.md').read_text(encoding='utf-8')\n",
        tmp_path,
    )
    assert events == []


def test_silent_on_another_file_in_the_same_directory(tmp_path: Path) -> None:
    events = _run(
        "import pathlib\npathlib.Path('NOTES.md').write_text('x', encoding='utf-8')\n",
        tmp_path,
    )
    assert events == []


def test_silent_on_a_same_named_file_elsewhere(tmp_path: Path) -> None:
    """CLAUDE.md ЧУЖОГО проекта — не наша цель.

    Фильтр сверяет abspath, а не basename; будь иначе, лента наполнилась бы
    записями во временные проекты, которые тесты создают десятками.
    """
    events = _run(
        "import pathlib\n"
        "other = pathlib.Path('other-project')\n"
        "other.mkdir()\n"
        "(other / 'CLAUDE.md').write_text('x', encoding='utf-8')\n",
        tmp_path,
    )
    assert events == []


# --- AC2: без переменных окружения хук НЕ СТАВИТСЯ ---------------------------


def test_not_installed_without_env(tmp_path: Path) -> None:
    """Не «поставлен и молчит», а не поставлен вовсе.

    Проверяется вместе с тем, что модуль ВСЁ ЖЕ был импортирован: иначе тест
    доказывал бы лишь то, что мы забыли положить каталог на PYTHONPATH.
    """
    events = _run(
        "import sys\n"
        "assert 'sitecustomize' in sys.modules, 'хук не был импортирован — тест ничего не проверил'\n"
        + WRITE_TARGET,
        tmp_path,
        arm=False,
    )
    assert events == []
    assert not (tmp_path / "audit.jsonl").exists()


def test_not_installed_with_root_but_no_log(tmp_path: Path) -> None:
    """Половина настройки — не настройка: писать некуда, значит хук не ставится."""
    log = tmp_path / "audit.jsonl"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(HOOK_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["CLAUDEMD_AUDIT_ROOT"] = str(tmp_path)
    env.pop("CLAUDEMD_AUDIT_LOG", None)
    proc = subprocess.run(
        [sys.executable, "-c", WRITE_TARGET],
        env=env,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert not log.exists()


# --- AC5: свойство, ради которого выбрана форма sitecustomize ----------------


def test_arms_itself_in_a_grandchild_process(tmp_path: Path) -> None:
    """Хук встаёт в подпроцессе, которого никто не инструментировал.

    Это ЕДИНСТВЕННАЯ причина, по которой инструмент назван sitecustomize, а не
    подключён фикстурой: порча приходила из процесса, порождённого тестом.
    Проверяется именно на внуке — pid в событии обязан отличаться от pid
    процесса, которому мы задали окружение.
    """
    child = (
        "import subprocess, sys, os, json\n"
        "p = subprocess.run([sys.executable, '-c', "
        "\"import pathlib; pathlib.Path('CLAUDE.md').write_text('x', encoding='utf-8')\"],\n"
        "    capture_output=True, text=True, encoding='utf-8')\n"
        "assert p.returncode == 0, p.stderr\n"
        "print(json.dumps({'parent_pid': os.getpid()}))\n"
    )
    log = tmp_path / "audit.jsonl"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(HOOK_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["CLAUDEMD_AUDIT_ROOT"] = str(tmp_path)
    env["CLAUDEMD_AUDIT_LOG"] = str(log)
    env.pop("PYTEST_XDIST_WORKER", None)
    proc = subprocess.run(
        [sys.executable, "-c", child],
        env=env,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    parent_pid = json.loads(proc.stdout.strip().splitlines()[-1])["parent_pid"]

    events = [
        json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert len(events) == 1
    assert events[0]["pid"] != parent_pid, (
        "событие пришло из процесса, которому окружение задали руками — "
        "распространение в подпроцесс НЕ проверено"
    )


# --- лента: форма события ----------------------------------------------------


@pytest.mark.parametrize("field", ["ts", "pid", "worker", "path", "mode", "cwd", "argv", "stack"])
def test_event_carries_every_field_the_investigation_needed(tmp_path: Path, field: str) -> None:
    """Поля перечислены поимённо: каждое из них однажды понадобилось в разборе."""
    events = _run(WRITE_TARGET, tmp_path)
    assert field in events[0]


def test_ledger_is_append_only_across_processes(tmp_path: Path) -> None:
    """Два процесса пишут в одну ленту, не затирая друг друга.

    В настоящем разборе лента наполнялась девятнадцатью воркерами сразу; лента,
    открытая на 'w', оставила бы одно последнее событие и увела бы разбор.
    """
    _run(WRITE_TARGET, tmp_path)
    _run(WRITE_TARGET, tmp_path)
    log = tmp_path / "audit.jsonl"
    events = [
        json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert len(events) == 2
