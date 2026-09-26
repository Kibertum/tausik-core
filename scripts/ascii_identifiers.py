"""Имена латиницей; проза остаётся на любом языке.

ПОЧЕМУ РАЗДЕЛЕНИЕ ИМЕННО ТАКОЕ. Имя — интерфейс. Его читают трассировки, grep,
отчёты покрытия, узлы pytest, чужие инструменты и люди, у которых нет русской
раскладки; ломается оно тихо — на кодировке консоли, на regex с `\\w`, на
обратной косой в `sh`. Докстринг и комментарий читает человек, и ни в одну
машинную поверхность они не попадают, поэтому язык прозы здесь не предмет.

ЗАМЕР, смена #277, с которого начата проверка: кириллических имён в `scripts`,
`bootstrap` и `harness` НОЛЬ; в `tests` — 269 в 20 файлах. Владелец наблюдает, что
проекты на TAUSIK объявляют переменные по-русски. Механизм виден из этих двух
чисел: продуктового кода на кириллице у нас нет, а домашний стиль агент считывает
по тестам и переносит в продукт.

ЧТО СЧИТАЕТСЯ ИМЕНЕМ. Всё, что попадает в пространство имён: функции, классы,
аргументы, цели присваивания, псевдонимы импорта, переменные `for`, `with` и
`except`, ключевые аргументы вызова. Строки, докстринги и комментарии не
проверяются вовсе — не «прощаются», а не читаются: проверка работает по AST.

ЧЕГО ЗДЕСЬ НЕТ: суждения о том, сколько имён допустимо. Порог — дело храповика,
и он объявлен в `tausik/gates.json`, а не спрятан здесь.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from ide_utils import all_profile_dirs

#: Любая буква вне ASCII в идентификаторе. Не только кириллица: имя на греческом
#: или с диакритикой ломается ровно так же, и перечислять алфавиты означало бы
#: пропускать следующий.
_NON_ASCII = re.compile(r"[^\x00-\x7f]")

#: Куда не заглядываем. Развёрнутые копии профилей — КОПИИ исходников: считать их
#: отдельными находками значило бы умножить одно нарушение на число хостов.
_SKIP_DIRS = frozenset({"__pycache__", ".git", "node_modules", "venv", ".venv"})
#: Профильные каталоги — из реестра IDE, а не списком здесь: свой список означает,
#: что добавленный хост молча не исключается, и сканер обойдёт копию движка.
#: `.tausik` добавлен отдельно — это не профиль IDE, а рабочее состояние с венвом.
_PROFILE_DIRS = all_profile_dirs() | {".tausik"}


def _names(tree: ast.AST) -> list[tuple[str, int]]:
    """Все объявляемые и связываемые имена дерева с номерами строк.

    `ast.Name` берётся только в контексте `Store`: чтение имени, объявленного в
    другом файле, — не объявление здесь, и считать его значило бы сообщать одно
    нарушение столько раз, сколько оно использовано.
    """
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.append((node.name, node.lineno))
        elif isinstance(node, ast.arg):
            found.append((node.arg, node.lineno))
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            found.append((node.id, node.lineno))
        elif isinstance(node, ast.keyword) and node.arg:
            found.append((node.arg, getattr(node, "lineno", 0)))
        elif isinstance(node, ast.alias):
            found.append((node.asname or node.name, getattr(node, "lineno", 0)))
        elif isinstance(node, ast.ExceptHandler) and node.name:
            found.append((node.name, node.lineno))
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            found.extend((n, node.lineno) for n in node.names)
    return found


def offenders_in_source(source: str) -> list[tuple[str, int]]:
    """Имена с не-ASCII символами. Нечитаемый файл даёт ПУСТО, а не отказ.

    Пустота на синтаксической ошибке — осознанный выбор: проверка стиля не должна
    падать на файле, который и без неё не собирается, иначе её выключат вместе с
    настоящей поломкой.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    seen: set[tuple[str, int]] = set()
    out: list[tuple[str, int]] = []
    for name, line in _names(tree):
        if _NON_ASCII.search(name) and (name, line) not in seen:
            seen.add((name, line))
            out.append((name, line))
    return out


def scan_tree(root: Path, subdirs: tuple[str, ...]) -> dict[str, list[tuple[str, int]]]:
    """Путь относительно `root` → найденные в нём имена. Чистые файлы отсутствуют.

    Отсутствие, а не пустой список: словарь потом читают как «сколько файлов
    затронуто», и запись с нулём испортила бы это число.
    """
    result: dict[str, list[tuple[str, int]]] = {}
    for sub in subdirs:
        base = root / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            parts = path.parts
            if any(p in _SKIP_DIRS or p in _PROFILE_DIRS for p in parts):
                continue
            try:
                found = offenders_in_source(path.read_text(encoding="utf-8"))
            except OSError:
                continue
            if found:
                result[path.relative_to(root).as_posix()] = found
    return result


def count(found: dict[str, list[tuple[str, int]]]) -> int:
    """Сколько имён всего. Файлы считает `len(found)`."""
    return sum(len(v) for v in found.values())


def report(found: dict[str, list[tuple[str, int]]], limit: int = 10) -> str:
    """Текст для человека: сколько, где и что именно.

    Отказ, называющий только число, отправляет читателя искать; поэтому здесь
    есть и файл, и строка, и само имя — то, чем правка начинается.
    """
    if not found:
        return "имён вне ASCII нет"
    lines = [f"имён вне ASCII: {count(found)} в {len(found)} файле(ах)"]
    for rel, items in list(found.items())[:limit]:
        shown = ", ".join(f"{n}:{ln}" for n, ln in items[:4])
        more = f" (+{len(items) - 4})" if len(items) > 4 else ""
        lines.append(f"  {rel}: {shown}{more}")
    if len(found) > limit:
        lines.append(f"  … и ещё {len(found) - limit} файл(ов)")
    return "\n".join(lines)


#: Каталоги, которые у ПОТРЕБИТЕЛЯ не его код: развёрнутые профили, окружения,
#: порождённые деревья и тесты. Тесты исключены не из снисхождения, а потому что
#: у них своя база: см. `ascii_identifiers` в `tausik/gates.json`.
_NOT_PRODUCT = frozenset({"tests", "test", "build", "dist", ".mypy_cache", ".pytest_cache", ".git"})


def scan_project(root: Path) -> dict[str, list[tuple[str, int]]]:
    """Продуктовый код ПРОЕКТА — любой `.py` вне профилей, окружений и тестов.

    Нужен там, где деревья называются иначе: у потребителя нет ни `scripts`, ни
    `harness`, и проверка, знающая только наши имена каталогов, у него покажет
    ноль на любом дереве. Ноль, полученный тем, что никуда не смотрели, —
    худший из возможных зелёных.
    """
    result: dict[str, list[tuple[str, int]]] = {}
    for path in sorted(root.rglob("*.py")):
        parts = path.relative_to(root).parts
        if any(p in _SKIP_DIRS or p in _PROFILE_DIRS or p in _NOT_PRODUCT for p in parts):
            continue
        try:
            found = offenders_in_source(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if found:
            result[path.relative_to(root).as_posix()] = found
    return result


def doctor_rows(root: str):
    """Строки для `doctor`: `(уровень, метка, сообщение)`.

    Уровень `warn`, а не `fail`: имя на кириллице — долг стиля, а не поломка, и
    ронять из-за него проверку здоровья значило бы, что её перестанут читать.
    Сообщение НАЗЫВАЕТ файл, строку и имя, потому что предупреждение без места
    правки не отличается от молчания.
    """
    label = "Identifier style"
    try:
        found = scan_project(Path(root))
    except Exception as e:  # noqa: BLE001 — падение проверки не смеет уронить doctor
        yield ("warn", label, f"could not validate: {e}")
        return
    if not found:
        yield ("ok", label, "all identifiers are ASCII — traces, grep and coverage stay readable")
        return
    yield ("warn", label, report(found, limit=5))
