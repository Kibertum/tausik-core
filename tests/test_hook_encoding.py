"""Сообщение надзорного механизма обязано читаться одинаково везде.

hook-stderr-encoding-locale-dependent. Хук cost-budget пишет в stderr строку
«2× hard cap reached — stop and re-plan». Символы × (U+00D7) и — (U+2014)
уходили в кодировке локали: b'2\\xd7 hard cap reached \\x97'. Тест читал вывод
через subprocess.run(text=True) БЕЗ encoding, то есть в кодировке родителя.
Обычно совпадало — и всё было зелено. Под `python -X utf8 -m pytest` родитель
декодирует UTF-8, ребёнок пишет cp1251, и UnicodeDecodeError в потоке-читателе
превращает stdout/stderr в None. Наружу это выходило как «TypeError: argument
of type 'NoneType' is not iterable» — сообщение, не намекающее на кодировку
ничем.

ПОЧЕМУ ГЕЙТ, А НЕ РАЗОВАЯ ПРАВКА (конвенция #236). Прод формально был закрыт:
все 26 вызовов в .claude/settings.json несут `-X utf8`. Но это гарантия в 26
копиях флага, а не в коде. 27-й хук, добавленный без флага, вернул бы дефект
молча. Поэтому проверяются ОБА конца независимо: хук чинит свои потоки сам, и
конфиг обязан нести флаг. Ни одна из проверок не является следствием другой.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_HOOKS_DIR = os.path.join(_ROOT, "scripts", "hooks")
_SETTINGS = os.path.join(_ROOT, ".claude", "settings.json")

if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from _common import force_utf8_io  # noqa: E402

GUARD_NAME = "force_utf8_io"


def _hook_files() -> list[str]:
    return sorted(
        os.path.join(_HOOKS_DIR, f)
        for f in os.listdir(_HOOKS_DIR)
        if f.endswith(".py") and f != "__init__.py"
    )


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """id() of every string node that is a docstring.

    Docstrings never reach a stream, so a Russian docstring must not make a
    hook look guilty. Comments need no handling at all — ast drops them.
    """
    out: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                out.add(id(first.value))
    return out


def _has_non_ascii_output_literal(tree: ast.AST) -> bool:
    docstrings = _docstring_nodes(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue
        if not node.value.isascii():
            return True
    return False


def _writes_to_a_stream(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == "print":
            return True
        if isinstance(fn, ast.Attribute) and fn.attr == "write":
            target = fn.value
            if isinstance(target, ast.Attribute) and target.attr in ("stdout", "stderr"):
                return True
    return False


def _calls_guard(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == GUARD_NAME:
                return True
    return False


def _classify(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    return {
        "name": os.path.basename(path),
        "non_ascii_output": _has_non_ascii_output_literal(tree),
        "writes": _writes_to_a_stream(tree),
        "guarded": _calls_guard(tree),
    }


# --- AC5: код чинит себя сам --------------------------------------------------


class TestEveryHookForcesUtf8:
    def test_hooks_emitting_non_ascii_call_the_guard(self):
        """Нарушители перечисляются ПОИМЁННО.

        Булево «что-то не так» на 26 файлах бесполезно: чинить придётся
        поиском, и гейт отключат раньше, чем починят.
        """
        offenders = [
            h["name"]
            for h in (_classify(p) for p in _hook_files())
            if h["non_ascii_output"] and h["writes"] and not h["guarded"]
        ]
        assert not offenders, (
            "эти хуки пишут не-ASCII в поток, но не форсируют UTF-8 — их "
            f"сообщение зависит от локали машины: {offenders}. "
            f"Добавь `from _common import {GUARD_NAME}` и вызов в точке входа."
        )

    def test_the_scan_actually_sees_the_hooks(self):
        """Страховка от гейта-пустышки: пустой список файлов дал бы зелёное."""
        files = _hook_files()
        assert len(files) >= 20, f"сканирование не нашло хуков: {files}"

    def test_the_scan_actually_finds_non_ascii(self):
        """Вторая страховка: если бы детектор не срабатывал НИ НА ЧЁМ,
        основной тест был бы зелёным по причине сломанного детектора."""
        flagged = [
            h["name"] for h in (_classify(p) for p in _hook_files()) if h["non_ascii_output"]
        ]
        assert flagged, "детектор не-ASCII не сработал ни на одном хуке — он сломан"


# --- AC6: вторая линия обороны, конфиг ---------------------------------------


def _hook_commands(settings_path: str) -> list[str]:
    with open(settings_path, encoding="utf-8") as f:
        settings = json.load(f)
    out: list[str] = []
    for entries in (settings.get("hooks") or {}).values():
        for entry in entries:
            for hook in entry.get("hooks") or []:
                cmd = hook.get("command") or ""
                if "hooks/" in cmd and cmd.endswith(".py"):
                    out.append(cmd)
    return out


def _host_profiles() -> list[str]:
    """Каждый сгенерированный конфиг хоста, а не только .claude.

    Профилей два (.claude, .qwen) и они генерируются РАЗНЫМИ функциями. Ровно
    поэтому проверять один и считать вывод распространяющимся на второй
    нельзя — это предположение, а не проверка.
    """
    return [
        p for p in (_SETTINGS, os.path.join(_ROOT, ".qwen", "settings.json")) if os.path.exists(p)
    ]


class TestSettingsKeepTheFlag:
    """Belt and braces: код и конфиг проверяются НЕЗАВИСИМО.

    Форсирование в коде делает флаг избыточным для потоков — но флаг влияет
    ещё и на кодировку чтения stdin и на локаль по умолчанию, поэтому он не
    снимается, а фиксируется.
    """

    def test_every_hook_invocation_passes_x_utf8(self):
        missing = [
            f"{os.path.basename(os.path.dirname(p))}: {c}"
            for p in _host_profiles()
            for c in _hook_commands(p)
            if "-X utf8" not in c
        ]
        assert not missing, f"вызовы хуков без `-X utf8`: {missing}"

    def test_the_settings_scan_is_not_empty(self):
        """Страховка: изменившийся формат settings.json дал бы пустой список
        и зелёный тест, ничего при этом не проверив."""
        for path in _host_profiles():
            cmds = _hook_commands(path)
            assert len(cmds) >= 15, f"разбор {path} не нашёл вызовов хуков: {cmds}"

    def test_both_host_profiles_are_actually_scanned(self):
        """Второй профиль легко забыть — он и был забыт в первой редакции
        этого гейта. Проверяется, что сканируется больше одного."""
        assert len(_host_profiles()) >= 2, (
            f"ожидались профили .claude и .qwen, найдено: {_host_profiles()}"
        )

    def test_the_generator_itself_emits_the_flag(self):
        """Источник, а не только артефакт.

        settings.json не хранится в репозитории как шаблон — его СТРОЯТ
        функции в bootstrap/. Хук, добавленный туда генератором без флага,
        оставался бы незамеченным до следующего прогона bootstrap, то есть
        гейт узнавал бы о регрессии позже, чем она попадала в прод.
        """
        import glob
        import re

        builders: list[str] = []
        offenders: list[str] = []
        for path in glob.glob(os.path.join(_ROOT, "bootstrap", "*.py")):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            for line in text.splitlines():
                # Строка, собирающая команду запуска хука.
                if re.search(r'return f".*python.*\{.*hooks.*\}/\{script\}', line):
                    builders.append(f"{os.path.basename(path)}: {line.strip()}")
                    if "-X utf8" not in line:
                        offenders.append(f"{os.path.basename(path)}: {line.strip()}")
        assert builders, "не найдено ни одной функции, строящей команду хука — гейт ослеп"
        assert not offenders, f"генератор команд хуков без `-X utf8`: {offenders}"


# --- AC2: поведение, а не форма кода -----------------------------------------


class TestHookOutputIsUtf8OnRawBytes:
    """Главный тест. Читает СЫРЫЕ БАЙТЫ и запускает хук БЕЗ -X utf8.

    Читать декодированную строку здесь бессмысленно: декодер родителя
    подогнал бы результат под ожидание, и тест доказал бы сам себя.
    """

    def _run_raw(self, tmp_path, source: str) -> bytes:
        script = tmp_path / "emit.py"
        script.write_text(source, encoding="utf-8")
        # Никакого -X utf8: воспроизводится ровно тот способ запуска, при
        # котором дефект и проявлялся.
        env = {**os.environ}
        env.pop("PYTHONIOENCODING", None)
        env.pop("PYTHONUTF8", None)
        p = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            env=env,
            cwd=str(tmp_path),
            timeout=30,
        )
        return p.stderr

    def test_unguarded_output_is_not_utf8_this_is_the_defect(self, tmp_path):
        """Опорная точка: без защиты вывод в кодировке локали.

        Если этот тест однажды позеленеет сам собой, значит среда сменилась и
        основной тест ниже перестал что-либо доказывать — тогда его надо
        пересматривать, а не радоваться.
        """
        raw = self._run_raw(
            tmp_path,
            'import sys\nprint("2× hard cap — stop", file=sys.stderr)\n',
        )
        if sys.getdefaultencoding() == "utf-8" and raw.decode("utf-8", "ignore").count("×"):
            pytest.skip("локаль этой машины уже UTF-8 — дефект здесь не воспроизводится")
        with pytest.raises(UnicodeDecodeError):
            raw.decode("utf-8")

    def test_guarded_output_is_utf8_regardless_of_invocation(self, tmp_path):
        """AC2: с защитой байты — UTF-8, хотя интерпретатор запущен без флага."""
        raw = self._run_raw(
            tmp_path,
            "import sys, os\n"
            f"sys.path.insert(0, {_HOOKS_DIR!r})\n"
            f"from _common import {GUARD_NAME}\n"
            f"{GUARD_NAME}()\n"
            'print("2× hard cap — stop", file=sys.stderr)\n',
        )
        decoded = raw.decode("utf-8")
        assert "2× hard cap — stop" in decoded, (
            f"вывод защищённого хука не читается как UTF-8: {raw!r}"
        )


# --- AC8: защита не может уронить хук ----------------------------------------


class TestGuardNeverRaises:
    def test_guard_is_idempotent(self):
        force_utf8_io()
        force_utf8_io()

    def test_guard_survives_streams_without_reconfigure(self, monkeypatch):
        """pytest подменяет потоки объектами захвата; io.StringIO тоже без
        reconfigure. Защита обязана быть no-op, а не падать."""
        import io

        monkeypatch.setattr(sys, "stdout", io.StringIO())
        monkeypatch.setattr(sys, "stderr", io.StringIO())
        force_utf8_io()

    def test_unencodable_character_degrades_instead_of_raising(self, tmp_path):
        """AC8: механизм, сообщающий о превышении бюджета, не имеет права
        упасть, пытаясь предупредить. errors='replace', а не strict."""
        raw = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys\n"
                f"sys.path.insert(0, {_HOOKS_DIR!r})\n"
                f"from _common import {GUARD_NAME}\n"
                f"{GUARD_NAME}()\n"
                'sys.stderr.write("ok \U0001f600 done\\n")\n',
            ],
            capture_output=True,
            timeout=30,
        )
        assert raw.returncode == 0, f"защита уронила процесс: {raw.stderr!r}"


# --- AC7 НЕГАТИВНЫЙ: гейт не срабатывает ложно -------------------------------


class TestGateDoesNotFireFalsely:
    """Гейт, дающий ложные срабатывания, будет отключён — и правильно."""

    def _tree(self, src: str):
        return ast.parse(src)

    def test_pure_ascii_hook_is_not_flagged(self):
        src = 'import sys\nprint("plain ascii only", file=sys.stderr)\n'
        assert _has_non_ascii_output_literal(self._tree(src)) is False

    def test_non_ascii_only_in_a_docstring_is_not_flagged(self):
        """Русский докстринг в поток не попадает никогда."""
        src = '"""Проверка кодировки."""\nimport sys\nprint("ascii", file=sys.stderr)\n'
        assert _has_non_ascii_output_literal(self._tree(src)) is False

    def test_non_ascii_only_in_a_comment_is_not_flagged(self):
        src = 'import sys\n# комментарий на русском\nprint("ascii", file=sys.stderr)\n'
        assert _has_non_ascii_output_literal(self._tree(src)) is False

    def test_a_module_that_never_writes_is_not_flagged(self):
        """Библиотечный модуль с русскими строками ничего не печатает."""
        src = 'MESSAGES = {"warn": "превышение"}\n'
        assert _writes_to_a_stream(self._tree(src)) is False

    def test_a_real_offender_is_flagged(self):
        """Позитивный контроль к четырём негативным: детектор не выродился
        в «всегда False», иначе все проверки выше проходили бы даром."""
        src = 'import sys\nprint("2× cap", file=sys.stderr)\n'
        tree = self._tree(src)
        assert _has_non_ascii_output_literal(tree) is True
        assert _writes_to_a_stream(tree) is True
        assert _calls_guard(tree) is False


# --- AC3: тестовый конец ------------------------------------------------------


class TestNoSilentEncodingInheritance:
    """subprocess.run(text=True) без encoding наследует кодировку родителя.

    Именно эта формула сделала пять тестов зависимыми от того, каким флагом
    запущен pytest. Проверяется весь каталог tests/, а не один файл: карточка
    прямо требовала обхода шире одного места.
    """

    def _offenders(self) -> list[str]:
        tests_dir = os.path.join(_ROOT, "tests")
        bad: list[str] = []
        for name in sorted(os.listdir(tests_dir)):
            if not name.startswith("test_") or not name.endswith(".py"):
                continue
            path = os.path.join(tests_dir, name)
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                is_run = (isinstance(fn, ast.Attribute) and fn.attr in ("run", "Popen")) or (
                    isinstance(fn, ast.Name) and fn.id in ("run", "Popen")
                )
                if not is_run:
                    continue
                kw = {k.arg for k in node.keywords if k.arg}
                # Бинарный режим (без text/universal_newlines) корректен сам по
                # себе: байты не декодируются, наследовать нечего.
                if ("text" in kw or "universal_newlines" in kw) and "encoding" not in kw:
                    bad.append(f"{name}:{node.lineno}")
        return bad

    def test_no_test_reads_a_subprocess_in_the_parents_encoding(self):
        offenders = self._offenders()
        assert not offenders, (
            "эти вызовы декодируют вывод дочернего процесса кодировкой "
            f"родителя и потому зависят от флагов запуска pytest: {offenders}. "
            'Добавь encoding="utf-8".'
        )

    def test_binary_mode_is_not_an_offender(self):
        """НЕГАТИВНЫЙ: без text=True декодирования нет, придираться не к чему."""
        src = "import subprocess\nsubprocess.run(['x'], capture_output=True)\n"
        tree = ast.parse(src)
        found = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "run"
            and {k.arg for k in n.keywords if k.arg} & {"text", "universal_newlines"}
        ]
        assert not found
