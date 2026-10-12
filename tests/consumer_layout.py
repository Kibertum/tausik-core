"""Раскладка ПОТРЕБИТЕЛЬСКОГО проекта — та, в которой TAUSIK ставится, а не пишется.

ЗАЧЕМ. TAUSIK разрабатывается там, где он И ЕСТЬ проект: `project_dir` и
`lib_dir` — один каталог, `scripts/` принадлежит харнессу, тесты лежат в
`<root>/tests`. Ставится он в противоположное: библиотека приходит сабмодулем
под `.tausik-lib`, `scripts/` принадлежит ПРОЕКТУ и содержит его собственные
скрипты, а тесты могут лежать где угодно — `backend/tests`, `services/api/tests`.

Каждое допущение о путях, верное дома, в этой раскладке переворачивается — и
переворачивается МОЛЧА, потому что дома все тесты зелёные. За два дня августа
2026 так нашлись пять дефектов подряд, все одного корня:

  * хуки указывали в сабмодуль, которого нет в обычном клоне;
  * гейт pytest искал тесты только в `<root>/tests` и молча вырождался в no-op;
  * doctor сравнивал дрейф с `<project>/scripts`, то есть с чужими файлами;
  * детектор соседних MCP требовал абсолютного пути в чужой командной строке;
  * защитный гейт memory-route в pre-commit не находил себя и молча не
    запускался — а `docs/en/security.md` обещает его работу.

Последний нашёлся адверсариальным ревью, а не этой фикстурой: она проверяла
пути, а не адрес гейта в shell-хуке. Проверка добавлена — фикстура существует
затем, чтобы следующий дефект того же класса ловился до выпуска, а не на живой
установке.

ЧЕГО ФИКСТУРА НЕ ДЕЛАЕТ. Она не поднимает процессы и не трогает сеть. Детектор
соседних MCP проверяется теперь не через неё, а напрямую через вынесенный
предикат `_command_belongs_to_project` — шов появился вместе с починкой, и до
него проверить дефект было нечем.

Что через фикстуру ПРОВЕРЯЕТСЯ помимо путей: разрешение адреса защитного гейта в
`scripts/hooks/pre-commit`. Для этого профиль содержит не одни хуки, а и
`gate_memory_route.py` — `copy_scripts` разворачивает весь `scripts/`, и без
этого файла фикстура утверждала бы, что движка у потребителя нет вовсе.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass(frozen=True)
class ConsumerProject:
    """Пути потребительского проекта, собранного фикстурой."""

    root: str
    lib: str
    own_scripts: str
    tests_dir: str
    ide_dir: str

    @property
    def deployed_scripts(self) -> str:
        return os.path.join(self.ide_dir, "scripts")

    @property
    def deployed_hooks(self) -> str:
        return os.path.join(self.ide_dir, "scripts", "hooks")


def build_consumer_project(
    tmp_path,
    *,
    ide: str = "claude",
    tests_at: str = os.path.join("backend", "tests"),
    empty_lib: bool = True,
) -> ConsumerProject:
    """Собрать проект в раскладке, в которой TAUSIK — подключённая библиотека.

    `empty_lib=True` воспроизводит клон без `--recurse-submodules`: каталог
    сабмодуля есть, содержимого нет. Это не крайний случай, а состояние по
    умолчанию для всякого, кто клонировал обычной командой.
    """
    root = tmp_path / "consumer"
    root.mkdir()

    # Библиотека как сабмодуль. Пустая — так выглядит обычный клон.
    lib = root / ".tausik-lib"
    (lib / "scripts" / "hooks").mkdir(parents=True)
    if not empty_lib:
        for name in _harness_hook_names():
            (lib / "scripts" / "hooks" / name).write_text("# библиотека\n", encoding="utf-8")

    # СОБСТВЕННЫЕ скрипты проекта — не харнесса. Именно из-за них doctor
    # рапортует дрейф на файлах, которые к TAUSIK отношения не имеют.
    own_scripts = root / "scripts"
    own_scripts.mkdir()
    for name in ("deploy.sh", "pg_backup.sh", "build_deck.py"):
        (own_scripts / name).write_text("# скрипт проекта\n", encoding="utf-8")

    # Тесты НЕ в <root>/tests — типовая раскладка монорепозитория и бэкенда.
    tests_dir = root / tests_at
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_quota.py").write_text(
        "def test_quota():\n    assert True\n", encoding="utf-8"
    )
    (tests_dir / "test_billing.py").write_text(
        "def test_billing():\n    assert True\n", encoding="utf-8"
    )

    # Исходники, на которые эти тесты отображаются по basename.
    src = root / "backend" / "app" / "services"
    src.mkdir(parents=True)
    (src / "quota.py").write_text("def charge():\n    return 1\n", encoding="utf-8")

    # Развёрнутый профиль IDE — то, что кладёт copy_scripts.
    ide_dir = root / f".{ide}"
    hooks = ide_dir / "scripts" / "hooks"
    hooks.mkdir(parents=True)
    for name in _harness_hook_names():
        (hooks / name).write_text("# развёрнутая копия\n", encoding="utf-8")
    # `copy_scripts` разворачивает ВЕСЬ `scripts/`, а не одни хуки, и гейты
    # ищутся именно здесь. Без этого файла фикстура утверждала бы, что у
    # потребителя движка нет вовсе, — а он есть, просто не там, где дома.
    (ide_dir / "scripts" / "gate_memory_route.py").write_text(
        "# развёрнутая копия гейта\n", encoding="utf-8"
    )

    return ConsumerProject(
        root=str(root),
        lib=str(lib),
        own_scripts=str(own_scripts),
        tests_dir=str(tests_dir),
        ide_dir=str(ide_dir),
    )


def _harness_hook_names() -> list[str]:
    """Имена хуков берутся из живого дерева, а не перечисляются руками.

    Список руками устарел бы на первом же новом хуке, и фикстура покраснела бы
    на себе, а не на дефекте.
    """
    hooks_dir = os.path.join(_REPO, "scripts", "hooks")
    return sorted(f for f in os.listdir(hooks_dir) if f.endswith(".py"))
