"""`init` создаёт проект там, где стоит пользователь, либо отказывает вслух.

Было: `cmd_init` звал `find_tausik_dir()`, то есть ИСКАЛ вместо того, чтобы
СОЗДАВАТЬ. Поиск отдавал первый `.tausik` выше по дереву — а на штатной
установке им оказывался пользовательский тир `~/.tausik`. В пустом каталоге
команда печатала

    Config already exists: C:\\Users\\<user>\\.tausik\\config.json
    Database: C:\\Users\\<user>\\.tausik\\tausik.db
    Project 'probe' initialized.

не создав ничего. Данные нового проекта уходили в тир, а сообщение об успехе
было ложным — самый дорогой вид тихого отказа, потому что проверять его никто
не станет.

Граница «тир — не проект» закрыта отдельно, в
`test_the_home_tier_is_not_a_project`. Здесь проверяется вторая половина: даже
когда предок НАСТОЯЩИЙ, усыновлять его молча нельзя.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_REPO, "scripts")
sys.path.insert(0, _SCRIPTS)

import project_config  # noqa: E402


def _run(cwd, *args, home=None):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("TAUSIK_DIR", None)
    if home is not None:
        env["HOME"] = str(home)
        env["USERPROFILE"] = str(home)
    return subprocess.run(
        [sys.executable, "-X", "utf8", os.path.join(_SCRIPTS, "project.py"), *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


@pytest.fixture
def home_with_a_tier(tmp_path):
    """Домашний каталог с пользовательским тиром — штатная установка."""
    home = tmp_path / "home"
    (home / project_config.TAUSIK_DIR).mkdir(parents=True)
    return home


def test_init_creates_the_project_in_the_current_directory(home_with_a_tier):
    """AC1: пустой каталог под домом с тиром — проект появляется ЗДЕСЬ."""
    fresh = home_with_a_tier / "fresh"
    fresh.mkdir()

    result = _run(fresh, "init", "--name", "probe", home=home_with_a_tier)

    assert result.returncode == 0, result.stderr
    assert (fresh / project_config.TAUSIK_DIR).is_dir(), (
        "проект не создан там, где стоял пользователь"
    )
    assert str(fresh) in result.stdout, (
        f"в отчёте назван чужой каталог: {result.stdout!r} — именно так дефект и выглядел"
    )


def test_the_user_tier_is_left_untouched(home_with_a_tier):
    """AC2: данные нового проекта не попадают в пользовательский тир.

    Проверяется байтами тира, а не только словами команды: сообщение об успехе
    как раз и было тем, что врало.
    """
    tier_db = home_with_a_tier / project_config.TAUSIK_DIR / "tausik.db"
    tier_db.write_bytes(b"pretend this is the user tier database")
    before = hashlib.md5(tier_db.read_bytes()).hexdigest()

    fresh = home_with_a_tier / "fresh"
    fresh.mkdir()
    _run(fresh, "init", "--name", "probe", home=home_with_a_tier)

    assert hashlib.md5(tier_db.read_bytes()).hexdigest() == before, (
        "init записал в пользовательский тир"
    )


def test_a_second_init_does_not_destroy_the_first(home_with_a_tier):
    """AC3 (НЕГАТИВНЫЙ): повторный init идемпотентен и не затирает данные.

    Лечение, сносящее существующий проект ради «чистой» инициализации, было бы
    хуже дефекта: тот терял новые данные, это потеряло бы старые.
    """
    fresh = home_with_a_tier / "fresh"
    fresh.mkdir()
    _run(fresh, "init", "--name", "probe", home=home_with_a_tier)
    marker = fresh / project_config.TAUSIK_DIR / "keep-me.txt"
    marker.write_text("данные, которых лишиться нельзя", encoding="utf-8")

    result = _run(fresh, "init", "--name", "probe", home=home_with_a_tier)

    assert result.returncode == 0, result.stderr
    assert marker.is_file(), "повторный init снёс содержимое существующего проекта"
    assert "already exists" in result.stdout


def test_init_inside_a_real_project_refuses_and_names_the_root(home_with_a_tier):
    """AC4 (НЕГАТИВНЫЙ): вложенный проект молча не заводится.

    У второго проекта будет своя база, и часть работы уедет в неё незаметно.
    Отказ обязан НАЗВАТЬ найденный корень: сообщение «здесь нельзя» без адреса
    оставляет пользователя гадать, что именно нашлось.
    """
    project = home_with_a_tier / "proj"
    project.mkdir()
    _run(project, "init", "--name", "outer", home=home_with_a_tier)
    inner = project / "src"
    inner.mkdir()

    result = _run(inner, "init", "--name", "nested", home=home_with_a_tier)

    assert result.returncode == 1
    assert str(project) in result.stderr, "отказ не назвал найденный корень"
    assert not (inner / project_config.TAUSIK_DIR).exists(), "вложенный проект всё-таки создан"


def test_the_nested_case_stays_reachable_with_here(home_with_a_tier):
    """НЕГАТИВНЫЙ к самому отказу: намеренный вложенный проект остаётся возможен.

    Отказ, который нельзя обойти, превращает лечение в новую болезнь — случай
    редкий, но законный, и запирать его наглухо не за что.
    """
    project = home_with_a_tier / "proj"
    project.mkdir()
    _run(project, "init", "--name", "outer", home=home_with_a_tier)
    inner = project / "src"
    inner.mkdir()

    result = _run(inner, "init", "--name", "nested", "--here", home=home_with_a_tier)

    assert result.returncode == 0, result.stderr
    assert (inner / project_config.TAUSIK_DIR).is_dir()
