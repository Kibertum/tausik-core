"""`~/.tausik` — пользовательский тир конфигурации, и проектом он не считается.

`config_trust` намеренно кладёт пользовательскую конфигурацию по той же
раскладке `.tausik/config.json`, что и проект, только в домашнем каталоге.
Восходящий поиск проекта отличить их не умел — и на Windows это срабатывало
ВСЕГДА, потому что любой временный каталог лежит под `C:\\Users\\<user>`, а
подъём на десять уровней доходит до дома с запасом.

Последствия были двумя, и обе — тихие:

* `tausik status`, набранный где угодно, показывал сводку пользовательского
  тира вместо отказа «проекта здесь нет»;
* `tausik init` в пустом каталоге печатал «Project 'probe' initialized»,
  не создав ничего, и данные нового проекта уходили в тир.

Плюс третье, обнаруженное этим же прогоном: собственный набор тестов писал в
`~/.tausik/tausik.db` разработчика — хеш файла менялся после прогона.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_REPO, "scripts")
sys.path.insert(0, _SCRIPTS)

import project_config  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Домашний каталог с пользовательским тиром — как на штатной установке."""
    home = tmp_path / "home"
    (home / project_config.TAUSIK_DIR).mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("TAUSIK_DIR", raising=False)
    return home


def test_the_home_tier_is_not_offered_as_a_project(fake_home, monkeypatch):
    """Подъём доходит до дома и НЕ выдаёт тир за проект.

    Стоим в каталоге под домом, где своего `.tausik` нет. Прежде поиск
    поднимался до `~/.tausik` и возвращал его; теперь возвращается
    несуществующий `cwd/.tausik` — ответ на вопрос «где проект БЫЛ БЫ».
    """
    elsewhere = fake_home / "Downloads" / "whatever"
    elsewhere.mkdir(parents=True)
    monkeypatch.chdir(elsewhere)

    found = project_config.find_tausik_dir()

    assert os.path.normcase(os.path.realpath(found)) != os.path.normcase(
        os.path.realpath(project_config.home_tier_dir())
    ), "пользовательский тир выдан за проект"
    assert not os.path.isdir(found), "проекта здесь нет, и найтись он не мог"


def test_a_real_project_inside_home_is_still_found(fake_home, monkeypatch):
    """НЕГАТИВНЫЙ: граница по РАВЕНСТВУ тиру, а не по вхождению в дом.

    Проекты живут в домашнем каталоге сплошь и рядом. Запрет, отрезающий всё
    под домом, сломал бы законный случай куда чаще, чем чинил бы дефект.
    """
    project = fake_home / "work" / "proj"
    (project / project_config.TAUSIK_DIR).mkdir(parents=True)
    inner = project / "src" / "deep"
    inner.mkdir(parents=True)
    monkeypatch.chdir(inner)

    found = project_config.find_tausik_dir()

    assert os.path.normcase(os.path.realpath(found)) == os.path.normcase(
        os.path.realpath(project / project_config.TAUSIK_DIR)
    ), "настоящий проект внутри дома обязан находиться"


def test_the_walk_does_not_climb_above_home(fake_home, monkeypatch):
    """Выше дома владения пользователя кончаются, и подъём туда не идёт.

    Одного запрета на сам тир мало: без остановки поиск просто перешагивал дом
    и усыновлял первое, что найдёт выше. А выше лежат каталоги, общие для всех
    учётных записей, — `.tausik` там к работающему пользователю отношения не
    имеет, и завести его может кто угодно.
    """
    above = fake_home.parent
    (above / project_config.TAUSIK_DIR).mkdir()
    elsewhere = fake_home / "Downloads"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    found = project_config.find_tausik_dir()

    assert os.path.normcase(os.path.realpath(found)) != os.path.normcase(
        os.path.realpath(above / project_config.TAUSIK_DIR)
    ), "подъём перешагнул дом и усыновил чужой каталог"
    assert not os.path.isdir(found)


def test_an_explicit_pointer_at_the_tier_is_obeyed(fake_home, monkeypatch):
    """НЕГАТИВНЫЙ: запрет относится к УГАДЫВАНИЮ, а не к выбору.

    Пользователь, назвавший каталог сам, знает, что делает. Если бы запрет
    распространялся и на явное указание, лечение отняло бы у него возможность,
    которой дефект не касался.
    """
    monkeypatch.chdir(fake_home)
    tier = str(fake_home / project_config.TAUSIK_DIR)
    monkeypatch.setenv("TAUSIK_DIR", tier)

    assert project_config.find_tausik_dir() == tier


def test_identity_is_resolved_not_spelled(fake_home, monkeypatch):
    """Тождество каталога решается `realpath`, а не сравнением написаний.

    Дефект пережил первую правку именно здесь: на Windows подъём приходит от
    `TMP`, записанного коротким именем 8.3 (`C:\\Users\\DEVELO~1\\...`), а
    `expanduser` отдаёт длинное. Строки не совпадали, каталог был тот же, и
    запрет пропускал тир насквозь.

    Проверяем через симлинк, потому что 8.3 воспроизводим не везде, а вопрос
    один и тот же: две разные записи одного каталога.
    """
    link = fake_home.parent / "home-by-another-name"
    try:
        os.symlink(str(fake_home), str(link), target_is_directory=True)
    except (OSError, NotImplementedError, AttributeError):
        pytest.skip("создание симлинков недоступно на этом хосте")

    monkeypatch.setenv("HOME", str(link))
    monkeypatch.setenv("USERPROFILE", str(link))
    elsewhere = fake_home / "Downloads"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    found = project_config.find_tausik_dir()

    assert not os.path.isdir(found), (
        "тир, записанный другим путём, — тот же самый каталог, "
        "и сравнение написаний обязано было это упустить"
    )


# --- отказ вместо создания на ходу -------------------------------------------


def test_a_read_command_outside_a_project_is_refused(fake_home, monkeypatch):
    """Команда чтения вне проекта ОТКАЗЫВАЕТ и ничего не создаёт.

    `SQLiteBackend.__init__` разворачивает каталог и схему по факту
    подключения — для `init` это верно, для остальных это означало, что
    `tausik status` в произвольном каталоге заводил там `.tausik/tausik.db` и
    печатал «Tasks: 0/0 done». Отказ был неотличим от честного ответа, а
    побочный эффект оставался на диске.
    """
    elsewhere = fake_home / "Downloads"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    with pytest.raises(ServiceError) as excinfo:
        project_config.assert_project_exists("status")

    message = str(excinfo.value)
    assert "нет проекта TAUSIK" in message
    assert "Ничего не создано" in message
    assert not os.path.isdir(elsewhere / project_config.TAUSIK_DIR), (
        "проверка сама ничего создавать не имеет права"
    )


def test_init_is_the_one_command_allowed_to_create(fake_home, monkeypatch):
    """НЕГАТИВНЫЙ: `init` обязан проходить — иначе проект не завести никогда."""
    elsewhere = fake_home / "new-project"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    project_config.assert_project_exists("init")  # не должно бросить


def test_a_command_inside_a_project_is_not_refused(fake_home, monkeypatch):
    """НЕГАТИВНЫЙ: внутри настоящего проекта отказа быть не должно."""
    project = fake_home / "work" / "proj"
    (project / project_config.TAUSIK_DIR).mkdir(parents=True)
    monkeypatch.chdir(project)

    project_config.assert_project_exists("status")  # не должно бросить


# --- та же проверка через живой CLI ------------------------------------------


def test_the_cli_refuses_outside_a_project_and_leaves_nothing_behind(fake_home, tmp_path):
    """Сквозная проверка: отказ приходит из настоящего запуска, а не из вызова
    функции. Внутренний контракт может быть верным, а точка входа его не звать —
    именно так дефект и жил."""
    elsewhere = fake_home / "Downloads"
    elsewhere.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["USERPROFILE"] = str(fake_home)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("TAUSIK_DIR", None)

    result = subprocess.run(
        [sys.executable, "-X", "utf8", os.path.join(_SCRIPTS, "project.py"), "status"],
        cwd=str(elsewhere),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 1, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "нет проекта TAUSIK" in result.stderr
    assert not os.path.isdir(elsewhere / project_config.TAUSIK_DIR), (
        "команда чтения оставила после себя проект"
    )
