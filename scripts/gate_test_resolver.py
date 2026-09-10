"""Map source files → existing test files via basename heuristic.

Extracted from gate_runner.py to keep that module under the filesize budget.
Used by the pytest gate's `{test_files_for_files}` substitution to scope
runs to relevant tests instead of the full suite.
"""

from __future__ import annotations

import ast
import json
import os

from tausik_utils import tausik_config_path

# Module-level constant a cross-cutting test declares to name the source trees it
# guards, e.g. CROSSCUTTING_SCOPE = ["scripts/hooks/", "bootstrap/"]. The resolver
# reads it statically (no import — a test module runs fixtures on import) and adds
# the test to a scoped run when a changed file falls under any prefix.
_CROSSCUTTING_CONST = "CROSSCUTTING_SCOPE"


def read_crosscutting_scope(test_path: str) -> list[str] | None:
    """Path prefixes a test declares it guards, or None if it declares nothing.

    Returns a list (possibly empty — the visible opt-out `CROSSCUTTING_SCOPE = []`,
    meaning "reviewed, not cross-cutting") when the module-level constant is a
    literal list/tuple; None when absent, unparseable, or not a literal. Never
    imports the module and never raises — a bad file simply reads as undeclared.
    """
    try:
        with open(test_path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except (OSError, SyntaxError, ValueError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == _CROSSCUTTING_CONST for t in node.targets):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError, SyntaxError):
            return None
        if isinstance(value, (list, tuple)):
            return [str(p).replace("\\", "/") for p in value]
        return None
    return None


def test_roots(base: str) -> list[str]:
    """Каталоги, в которых лежат тесты. Обнаруживаются, а не предполагаются.

    Прежде путь `<base>/tests` был захардкожен в трёх местах, и в проекте с
    раскладкой `backend/tests/` индекс тестов выходил пустым. Дальше по цепочке
    `run_command_gate` попадал в ветку «нет замапленных тестов» и возвращал
    SKIP — неотличимый от честного «изменение действительно не мапится ни на
    один тест». Блокирующий гейт был включён, резолвился, показывался в
    `gates status` и не проверял НИЧЕГО.

    Настраивается ключом `testing.roots` в `.tausik/config.json`; при его
    отсутствии остаётся прежнее поведение — `<base>/tests`, если он есть.
    Пустой список означает «корней нет», и это ОТДЕЛЬНЫЙ исход, а не пустое
    отображение: см. `NoTestRootsError` и `assert_test_roots`.
    """
    roots: list[str] = []
    configured = _configured_roots(base)
    for rel in configured:
        # normpath: настроенный корень пишут через `/` даже на Windows, а
        # обнаруженные приходят с разделителем платформы. Без приведения одна и
        # та же функция отдавала бы корни в двух написаниях в зависимости от
        # того, настроены они или найдены, и сравнивающий их вызывающий читал
        # бы разные строки как разные каталоги.
        candidate = os.path.normpath(os.path.join(base, rel))
        if os.path.isdir(candidate):
            roots.append(candidate)
    if roots:
        return roots  # явная настройка побеждает обнаружение

    default = os.path.join(base, "tests")
    if os.path.isdir(default):
        return [default]
    return _discover_roots(base)


#: Каталоги, внутрь которых обнаружение не заходит. Чужой `tests/` в вендоренном
#: дереве — не наши тесты, и включить его значит гонять чужой набор под видом
#: своего.
_DISCOVERY_SKIP_BASE = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        "site-packages",
        "vendor",
        ".tausik",
        ".tausik-lib",
    }
)


def _discovery_skip() -> frozenset[str]:
    """Каталоги, внутрь которых обнаружение не заходит.

    Профили IDE берутся из ``ide_utils.all_profile_dirs``, а не перечисляются
    руками: список руками покрывал бы ``.claude`` и пропускал остальные шесть,
    и обнаружение зашло бы в развёрнутую копию движка, приняв её тесты за тесты
    проекта. Чужой ``tests/`` в вендоренном дереве — тоже не наши тесты, и
    включить его значит гонять чужой набор под видом своего.
    """
    from ide_utils import all_profile_dirs

    return _DISCOVERY_SKIP_BASE | all_profile_dirs()


#: Насколько глубоко искать. Глубина считается В СЕГМЕНТАХ ПУТИ до самого
#: `tests`: 2 — это `backend/tests`, 3 — `services/api/tests`. Обе раскладки
#: типовые для монорепозитория, и обе названы обещанием ниже по коду, поэтому
#: предел ровно 3.
#:
#: Прежнее значение 2 обещало `services/api/tests` докстрингом, а доставало
#: только до `backend/tests`: тот же дефект по форме, что и захардкоженный
#: `<root>/tests`, который эта функция и заводилась чинить, — только уровнем
#: ниже. `test_roots()` на дереве с `services/api/tests` возвращал пустой
#: список, гейт цитирования читал честную ссылку как выдуманную, а командный
#: гейт вырождался в SKIP.
#:
#: Глубже трёх не идём: обход всего дерева стоит дорого, а риск подцепить чужой
#: `tests/` растёт быстрее пользы. Кому нужно глубже — задаёт `testing.roots`.
_DISCOVERY_DEPTH = 3


def _discover_roots(base: str) -> list[str]:
    """Найти каталоги `tests` неглубоко под корнем проекта.

    Настройка `testing.roots` — правильный способ, но она требует ЗНАТЬ, что её
    надо задать. Пользователь с раскладкой `backend/tests` этого не знает: у него
    просто молча ничего не проверяется, и SKIP выглядит как честный. Поэтому
    обнаружение делает очевидный случай работающим без конфига, оставаясь
    ограниченным по глубине и по списку пропускаемых каталогов.
    """
    found: list[str] = []
    skip = _discovery_skip()
    for depth in range(1, _DISCOVERY_DEPTH + 1):
        _walk_level(base, base, depth, found, skip)
        if found:
            break  # ближайший уровень побеждает: глубже искать незачем
    return sorted(found)


def _walk_level(
    base: str, current: str, remaining: int, found: list[str], skip: frozenset[str]
) -> None:
    try:
        entries = sorted(os.listdir(current))
    except OSError:
        return
    for name in entries:
        if name in skip:
            continue
        path = os.path.join(current, name)
        if not os.path.isdir(path):
            continue
        if remaining == 1:
            if name == "tests":
                found.append(path)
        else:
            _walk_level(base, path, remaining - 1, found, skip)


def _configured_roots(base: str) -> list[str]:
    """`testing.roots` из конфига проекта. Ошибка чтения — не корни, а пусто."""
    path = tausik_config_path(base)
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError):
        return []
    testing = cfg.get("testing")
    if not isinstance(testing, dict):
        return []
    roots = testing.get("roots")
    if not isinstance(roots, list):
        return []
    return [str(r) for r in roots if isinstance(r, (str, os.PathLike))]


class NoTestRootsError(RuntimeError):
    """Корней с тестами не найдено — гейт не может определить область.

    Отличается от «изменение не мапится ни на один тест» намеренно. Первое —
    неверная настройка проекта, второе — законный результат. Сваливать их в
    один SKIP значит прятать первое за вторым, и ровно так дефект прожил
    незамеченным.
    """


def assert_test_roots(base: str) -> list[str]:
    """Корни или громкий отказ. Зовётся там, где SKIP был бы ложью."""
    roots = test_roots(base)
    if not roots:
        raise NoTestRootsError(
            "не найдено ни одного корня с тестами: нет ни `testing.roots` в "
            ".tausik/config.json, ни каталога tests/ в корне проекта. Гейт не "
            "может определить область — это НЕ то же самое, что «изменение не "
            "мапится ни на один тест», и молчаливым SKIP не подаётся."
        )
    return roots


def _crosscutting_index(base: str) -> dict[str, list[str]]:
    """{test_relpath: [prefixes]} for every declaring test under tests/.

    Text-filters to files that mention the constant before parsing, so the common
    case (a test that does not declare one) costs a cheap substring check, not an
    AST parse of all ~300 test files."""
    index: dict[str, list[str]] = {}
    for tests_root in test_roots(base):
        try:
            walker = os.walk(tests_root)
        except OSError:
            continue
        for dirpath, _dirnames, filenames in walker:
            for fn in filenames:
                if not (fn.startswith("test_") and fn.endswith(".py")):
                    continue
                abs_path = os.path.join(dirpath, fn)
                try:
                    with open(abs_path, encoding="utf-8") as fh:
                        if _CROSSCUTTING_CONST not in fh.read():
                            continue
                except OSError:
                    continue
                scope = read_crosscutting_scope(abs_path)
                if scope:  # non-empty list only; [] opt-out and None both skip
                    rel = os.path.relpath(abs_path, base).replace("\\", "/")
                    index[rel] = scope
    return index


def top_level_imports(text: str) -> set[str]:
    """Top-level imported modules, or an empty set when parsing fails."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module.split(".")[0])
    return out


def _tests_importing(base: str, modules: set[str], tests_index: dict[str, list[str]]) -> set[str]:
    """Find depth-one import edges; transitive imports deliberately do not count."""
    if not modules:
        return set()
    out: set[str] = set()
    for paths in tests_index.values():
        for rel in paths:
            try:
                with open(os.path.join(base, rel.replace("/", os.sep)), encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                continue
            if not any(m in text for m in modules):
                continue
            if modules & top_level_imports(text):
                out.add(rel)
    return out


def parse_errors_for_relevant(relevant_files: list[str] | None, *, root: str | None = None) -> list[str]:
    """Name candidate test sources the import resolver could not parse."""
    if not relevant_files:
        return []
    base = root or os.getcwd()
    modules = {
        os.path.splitext(os.path.basename(path.replace("\\", "/")))[0]
        for path in relevant_files
        if isinstance(path, str) and path.endswith(".py")
    }
    if not modules:
        return []
    errors: list[str] = []
    for paths in build_tests_index(base).values():
        for rel in paths:
            try:
                with open(os.path.join(base, rel.replace("/", os.sep)), encoding="utf-8") as fh:
                    text = fh.read()
                if not any(module in text for module in modules):
                    continue
                ast.parse(text)
            except (OSError, SyntaxError, ValueError):
                errors.append(rel)
    return sorted(errors)


def direct_import_count_for_relevant(relevant_files: list[str] | None, *, root: str | None = None) -> int:
    """Count depth-one import edges for an honest scoped-pytest label."""
    if not relevant_files:
        return 0
    base = root or os.getcwd()
    modules = {
        os.path.splitext(os.path.basename(path.replace("\\", "/")))[0]
        for path in relevant_files
        if isinstance(path, str) and path.endswith(".py")
    }
    return len(_tests_importing(base, modules, build_tests_index(base)))


def _basename_matches(stem: str, tests_index: dict[str, list[str]]) -> list[str]:
    """Return exact and suffix basename matches for a source stem."""
    out: list[str] = []
    out.extend(tests_index.get(f"test_{stem}.py", []))
    prefix = f"test_{stem}_"
    for fn, paths in tests_index.items():
        if fn.startswith(prefix) and fn.endswith(".py"):
            out.extend(paths)
    return out


def _under_prefix(path: str, prefix: str) -> bool:
    """True when `path` lies at or under `prefix`, respecting directory bounds:
    `scripts/hooks/` matches `scripts/hooks/x.py` but not `scripts/hooks_x/y.py`."""
    path = path.replace("\\", "/")
    prefix = prefix.replace("\\", "/").rstrip("/")
    if not prefix:
        return False
    return path == prefix or path.startswith(prefix + "/")


def _is_global_tree_prefix(prefix: str) -> bool:
    """Whether a declaration names an entire top-level repository tree."""
    return len([part for part in prefix.replace("\\", "/").strip("/").split("/") if part]) == 1


def deferred_global_crosscutting_for_relevant(
    relevant_files: list[str] | None, *, root: str | None = None
) -> set[str]:
    """Global guards matching this scope but deferred to the full/release lane."""
    if not relevant_files:
        return set()
    base = root or os.getcwd()
    rels = [r.replace("\\", "/") for r in relevant_files if r and isinstance(r, str)]
    return {
        test_rel
        for test_rel, prefixes in _crosscutting_index(base).items()
        if any(_is_global_tree_prefix(p) and _under_prefix(rel, p) for rel in rels for p in prefixes)
    }


def build_tests_index(base: str) -> dict[str, list[str]]:
    """Bucket every `tests/**/test_*.py` under `base` by basename.

    Walk tests/ once; supports nested layouts (tests/integration/test_foo.py).
    Permission errors / missing tests/ → empty index, callers fall back.

    Public because the pytest gate needs the DENOMINATOR of its own scope: a
    scoped run that reports "PASS" without saying "2 of 318 test files" reads
    as a statement about the whole project. See `run_command_gate`.
    """
    tests_index: dict[str, list[str]] = {}
    for tests_root in test_roots(base):
        try:
            for dirpath, _dirnames, filenames in os.walk(tests_root):
                for fn in filenames:
                    if not (fn.startswith("test_") and fn.endswith(".py")):
                        continue
                    abs_path = os.path.join(dirpath, fn)
                    rel_path = os.path.relpath(abs_path, base).replace("\\", "/")
                    tests_index.setdefault(fn, []).append(rel_path)
        except OSError:
            continue
    return tests_index


def count_test_files(root: str | None = None) -> int:
    """How many test files exist in total — the denominator of a scoped run."""
    return sum(len(paths) for paths in build_tests_index(root or os.getcwd()).values())


def resolve_test_files_for_relevant(
    relevant_files: list[str] | None, *, root: str | None = None
) -> list[str]:
    """Resolve observed, basename, depth-one-import and narrow declared edges."""
    if not relevant_files:
        return []
    base = root or os.getcwd()
    found: list[str] = []
    seen: set[str] = set()

    def _add(path: str) -> None:
        norm = path.replace("\\", "/")
        if norm in seen:
            return
        seen.add(norm)
        found.append(norm)

    tests_index = build_tests_index(base)
    changed_modules: set[str] = set()

    for raw in relevant_files:
        if not raw or not isinstance(raw, str):
            continue
        rel = raw.replace("\\", "/")
        # If the entry already points at a test file, accept it as-is.
        if "/tests/" in f"/{rel}" or os.path.basename(rel).startswith("test_"):
            abs_p = rel if os.path.isabs(rel) else os.path.join(base, rel)
            if os.path.isfile(abs_p):
                _add(rel)
                continue
        stem = os.path.splitext(os.path.basename(rel))[0]
        if not stem:
            continue
        if rel.endswith(".py"):
            changed_modules.add(stem)
        for path in _basename_matches(stem, tests_index):
            _add(path)

    # Import edge: a changed module pulls in every test that imports it, whatever
    # either one is called. Additive like the rest — a module nobody imports adds
    # nothing, and no branch here can widen the run to the whole suite.
    for test_rel in sorted(_tests_importing(base, changed_modules, tests_index)):
        _add(test_rel)

    # Cross-cutting tests: a declared CROSSCUTTING_SCOPE prefix that any changed
    # file falls under pulls the test in — BY PATH, not basename. This is additive
    # only: it never falls back to the full suite (that promise is the caller's),
    # and a change matching no prefix adds nothing.
    cc_index = _crosscutting_index(base)
    if cc_index:
        rels = [r.replace("\\", "/") for r in relevant_files if r and isinstance(r, str)]
        for test_rel, prefixes in cc_index.items():
            if any(
                not _is_global_tree_prefix(p) and _under_prefix(f, p)
                for f in rels
                for p in prefixes
            ):
                _add(test_rel)

    # OBSERVED, added last in code and FIRST in authority. Order here is only
    # de-duplication order; what matters is that the name/import/scope edges
    # above remain a fallback rather than being replaced. A graph with nothing
    # observed yet must select exactly what it selected before this existed —
    # "no observation" is not a claim that no test covers the file.
    for test_rel in sorted(_observed_tests_for(base, relevant_files)):
        _add(test_rel)
    return found


def _observed_tests_for(base: str, relevant_files: list[str] | None) -> set[str]:
    """Test files the GRAPH observed reaching any of `relevant_files`.

    Empty whenever the graph is unreachable, empty, or has never been fed an
    observation — all of which mean "we do not know", never "nothing covers
    this". The caller adds this to the name-based edges rather than replacing
    them, so an unknown answer costs nothing.
    """
    if not relevant_files:
        return set()
    db = os.path.join(base, ".tausik", "tausik.db")
    if not os.path.isfile(db):
        return set()

    wanted = [r.replace("\\", "/") for r in relevant_files if r and isinstance(r, str)]
    if not wanted:
        return set()

    import sqlite3

    placeholders = ",".join("?" for _ in wanted)
    try:
        with sqlite3.connect(db, timeout=2) as conn:
            rows = conn.execute(
                "SELECT src.path FROM artifact_edges e "
                "JOIN artifacts src ON src.id = e.source_artifact_id "
                "JOIN artifacts dst ON dst.id = e.target_artifact_id "
                "WHERE e.layer = 'observed_coverage' "
                f"AND dst.path IN ({placeholders})",
                wanted,
            ).fetchall()
    except sqlite3.Error:
        return set()
    return {
        str(row[0])
        for row in rows
        if os.path.isfile(os.path.join(base, str(row[0])))
    }
