"""Раскладка ПОТРЕБИТЕЛЬСКОГО проекта — та, в которой TAUSIK ставится, а не пишется.

ЗАЧЕМ. TAUSIK разрабатывается там, где он И ЕСТЬ проект: `project_dir` и
`lib_dir` — один каталог, `scripts/` принадлежит харнессу, тесты лежат в
`<root>/tests`. Ставится он в противоположное: библиотека приходит сабмодулем
под `.tausik-lib`, `scripts/` принадлежит ПРОЕКТУ и содержит его собственные
скрипты, а тесты могут лежать где угодно — `backend/tests`, `services/api/tests`.

Каждое допущение о путях, верное дома, в этой раскладке переворачивается — и
переворачивается МОЛЧА, потому что дома все тесты зелёные. За два дня августа
2026 так нашлись четыре дефекта подряд, все одного корня:

  * хуки указывали в сабмодуль, которого нет в обычном клоне (исправлено);
  * гейт pytest ищет тесты только в `<root>/tests` и молча вырождается в no-op;
  * doctor сравнивает дрейф с `<project>/scripts`, то есть с чужими файлами;
  * детектор соседних MCP требует абсолютного пути в чужой командной строке.

Эта фикстура существует, чтобы пятый дефект того же класса ловился до выпуска,
а не на живой установке.

ЧЕГО ФИКСТУРА НЕ ДЕЛАЕТ. Она не поднимает процессы и не трогает сеть, поэтому
детектор соседних MCP через неё не проверяется: у него нет отдельного предиката,
пригодного для вызова, — сопоставление вкраплено в обход процессов. Шов туда
выносится задачей sibling-mcp-detector-is-blind-to-a-relative-launch-path, и
тогда проверка добавляется сюда. Названо вслух, чтобы отсутствие проверки не
читалось как её успешное прохождение.
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
