"""Стек, объявляющий расширения, обязан иметь хотя бы один достижимый гейт.

Механический гейт вместо разовой правки (конвенция #236). Повод — запрос
владельца в сессии #121: «для flutter не оказалось гейтов». Обход реестра
показал, что flutter не один: у .dart кандидатный стек ровно {flutter}, у
.swift ровно {swift}, и НИ ОДИН гейт не перечислял их в своём `stacks`.

ПОЧЕМУ ЭТО ДЕФЕКТ, А НЕ ОТСУТСТВИЕ ФИЧИ. Для задачи с дартовыми файлами не
запускался ни линтер, ни компилятор, ни тесты — отрабатывали только
универсальные встроенные (filesize, renar drift), и `task done` рапортовал
зелено. Это ЗЕЛЁНЫЙ ВЕРДИКТ, НЕ ОЗНАЧАЮЩИЙ НИЧЕГО — тот же класс, что
verify-summary-reports-skipped-as-pass и verify-no-test-mapped-dead-end. Причём
здесь хуже: там прогон хотя бы честно помечался skipped, а тут гейтов нет
вовсе, и отличить «проверено» от «проверять было нечем» нельзя ни по одному
признаку в выводе.

ЧТО ИМЕННО ДЕРЖИТ ЭТОТ ФАЙЛ. Не наличие flutter/swift — их можно было
дописать и закрыть задачу. Он держит КЛАСС: стек номер 26 приедет с той же
дырой, и поймать его должен гейт, а не следующий случайный запрос владельца.

НАСЛЕДОВАНИЕ УЧИТЫВАЕТСЯ. Требовать собственных гейтов у каждого стека было бы
неверно и вредно: django/fastapi/flask ловятся pytest из python, react/next/
nuxt/vue/svelte — eslint/js-test/tsc из javascript и typescript, laravel — php,
blade — через отображение .blade.php в php. Такой гейт потребовал бы девяти
бессмысленных правок и был бы отключён первым же, кому он помешал. Поэтому
проверяется ДОСТИЖИМОСТЬ гейта для файлов стека, а не место его объявления.
"""

from __future__ import annotations

import glob
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from default_gates import DEFAULT_GATES  # noqa: E402
from gate_stack_dispatch import gate_applies_to, infer_stacks_from_files  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_STACKS_DIR = os.path.join(_ROOT, "stacks")


def _stack_decls() -> list[dict]:
    """Разобранные stack.json всех встроенных стеков."""
    out = []
    for path in sorted(glob.glob(os.path.join(_STACKS_DIR, "*", "stack.json"))):
        with open(path, encoding="utf-8") as fh:
            decl = json.load(fh)
        decl["_path"] = os.path.relpath(path, _ROOT)
        out.append(decl)
    return out


def _stacks_with_extensions() -> list[dict]:
    return [d for d in _stack_decls() if d.get("extensions")]


def _reachable_gates(extensions: list[str], registry: dict[str, dict]) -> list[str]:
    """Гейты, которые РЕАЛЬНО запустятся для файлов с такими расширениями.

    Достижимость считается тем же кодом, которым её считает прод
    (`gate_applies_to`), а не повторной реализацией правила. Вторая копия
    правила разошлась бы с первой молча — конвенция #249.
    """
    probe = [f"probe{ext}" for ext in extensions]
    return sorted(
        name
        for name, cfg in registry.items()
        if cfg.get("stacks") and gate_applies_to({**cfg, "name": name}, probe)
    )


def _stack_ids() -> list[str]:
    return [d["name"] for d in _stacks_with_extensions()]


@pytest.mark.parametrize("decl", _stacks_with_extensions(), ids=_stack_ids())
def test_every_stack_with_extensions_has_a_reachable_gate(decl):
    """AC4: сирот быть не должно.

    Параметр — стек, а не общий список: имя упавшего параметра сразу называет,
    КАКОЙ стек осиротел, без чтения сообщения.
    """
    reachable = _reachable_gates(decl["extensions"], DEFAULT_GATES)
    assert reachable, (
        f"стек '{decl['name']}' ({decl['_path']}) объявляет "
        f"extensions={decl['extensions']}, но для его файлов не запускается НИ ОДИН "
        "стек-гейт. Это зелёный вердикт, не означающий ничего: отличить "
        "«проверено» от «проверять было нечем» в выводе нельзя. Либо объяви "
        "gates в его stack.json (форма — stacks/go/stack.json), либо перечисли "
        "стек в поле `stacks` подходящего родительского гейта."
    )


class TestInheritanceIsRespected:
    """Гейт не требует своих гейтов там, где работает родительский.

    Без этого он потребовал бы девяти бессмысленных правок — и был бы
    отключён, как всякий гейт, который чаще мешает, чем ловит.
    """

    @pytest.mark.parametrize(
        "stack,parent_gate",
        [
            ("django", "pytest"),
            ("fastapi", "pytest"),
            ("flask", "pytest"),
            ("react", "eslint"),
            ("next", "eslint"),
            ("nuxt", "eslint"),
            ("vue", "eslint"),
            ("svelte", "eslint"),
            ("laravel", "phpstan"),
        ],
    )
    def test_a_child_stack_is_covered_by_its_parent(self, stack, parent_gate):
        decl = next(d for d in _stack_decls() if d["name"] == stack)
        reachable = _reachable_gates(decl["extensions"], DEFAULT_GATES)
        assert parent_gate in reachable, (
            f"'{stack}' перестал покрываться родительским гейтом '{parent_gate}' "
            f"(достижимы: {reachable}). Либо восстанови покрытие, либо объяви "
            "стеку собственные гейты — молча осиротеть он не имеет права."
        )

    def test_blade_is_covered_through_the_double_extension(self):
        """У blade покрытие держится на отображении .blade.php в php.

        Проверяется отдельно, потому что механизм у него ДРУГОЙ: не родительский
        стек, а двойное расширение, которое infer_stacks_from_files разбирает
        особым случаем. Общий параметризованный тест этого не показал бы.
        """
        stacks = infer_stacks_from_files(["resources/views/page.blade.php"])
        assert "php" in stacks, f"'.blade.php' больше не отображается в php: {sorted(stacks)}"
        assert _reachable_gates([".blade.php"], DEFAULT_GATES)


class TestTheCoverageGateActuallyCatchesAnOrphan:
    """Гейт, который никогда ничего не ловил, — гейт-гипотеза.

    Сегодня сирот нет, поэтому основной тест зелёный по причине «нечего
    ловить». Отличить это от «сломан и не ловит ничего» можно только внесённой
    сиротой.
    """

    def test_an_orphan_stack_is_detected(self):
        """AC6: внесённая сирота обязана быть найдена."""
        assert _reachable_gates([".nosuchlang"], DEFAULT_GATES) == []

    def test_a_gate_that_names_the_stack_makes_it_reachable(self):
        """Обратная сторона: как только гейт называет стек — сирота исчезает.

        Без этой половины тест выше проходил бы и на функции, всегда
        возвращающей пустой список.
        """
        registry = {
            **DEFAULT_GATES,
            "probe-gate": {
                "enabled": False,
                "severity": "warn",
                "trigger": ["verify"],
                "command": "true",
                "stacks": ["python"],
            },
        }
        assert "probe-gate" in _reachable_gates([".py"], registry)

    def test_the_measured_orphans_are_the_two_that_were_fixed(self):
        """Замер из карточки закреплён: сиротами были ровно flutter и swift.

        Проверяется на реестре БЕЗ их собственных гейтов — то есть
        воспроизводится исходное состояние, а не пересказывается.
        """
        stripped = {
            name: cfg
            for name, cfg in DEFAULT_GATES.items()
            if not (set(cfg.get("stacks") or []) & {"flutter", "swift"})
        }
        orphans = sorted(
            d["name"]
            for d in _stacks_with_extensions()
            if not _reachable_gates(d["extensions"], stripped)
        )
        assert orphans == ["flutter", "swift"], (
            f"состав сирот до правки изменился: {orphans}. Это осознанное решение, "
            "а не правка ожидаемого списка под факт."
        )


class TestTheCoverageGateIsNotHollow:
    """Без этих страховок гейт сравнивал бы пустое с пустым и был бы вечно зелёным."""

    def test_the_stack_list_is_not_empty(self):
        decls = _stacks_with_extensions()
        assert len(decls) >= 20, f"обход реестра стеков сломан: {[d['name'] for d in decls]}"
        names = {d["name"] for d in decls}
        assert {"python", "flutter", "swift"} <= names

    def test_the_extension_map_is_not_empty(self):
        """Отображение расширение→стек непусто — иначе достижимость всегда пуста."""
        assert infer_stacks_from_files(["a.py"]) >= {"python"}
        assert infer_stacks_from_files(["a.dart"]) == {"flutter"}
        assert infer_stacks_from_files(["a.swift"]) == {"swift"}

    def test_the_registry_has_stack_scoped_gates(self):
        scoped = [n for n, c in DEFAULT_GATES.items() if c.get("stacks")]
        assert len(scoped) >= 15, f"стек-гейтов в реестре всего {len(scoped)}: {scoped}"


class TestTheNewGatesAreDeclaredNotExecuted:
    """AC8: проверяется СТРУКТУРА объявления, а не результат запуска.

    Тулчейна Flutter и Swift на машине сборки нет. Тест, зовущий `flutter test`,
    падал бы у всех и был бы отключён в первый же день — то есть заменил бы
    молчаливую дыру шумным враньём.
    """

    _EXPECTED = {
        "dart-analyze": ("flutter", "block", "verify", "dart analyze"),
        "dart-format": ("flutter", "warn", "commit", "dart format"),
        "flutter-test": ("flutter", "block", "verify", "flutter test"),
        "swift-build": ("swift", "block", "verify", "swift build"),
        "swiftlint": ("swift", "warn", "commit", "swiftlint"),
        "swift-test": ("swift", "block", "verify", "swift test"),
    }

    @pytest.mark.parametrize("name", sorted(_EXPECTED))
    def test_gate_is_registered_with_the_declared_shape(self, name):
        stack, severity, trigger, fragment = self._EXPECTED[name]
        assert name in DEFAULT_GATES, f"гейт '{name}' не попал в реестр — объявление мёртвый текст"
        gate = DEFAULT_GATES[name]
        assert gate["stacks"] == [stack]
        assert gate["severity"] == severity
        assert trigger in gate["trigger"]
        assert fragment in gate["command"]
        assert gate["enabled"] is False, (
            f"'{name}' включён по умолчанию — тулчейна на машине сборки нет, "
            "и включённый гейт уронил бы всех"
        )

    def test_heavy_gates_run_on_verify_not_task_done(self):
        """Verify-First (QG-2): тяжёлое — на verify, а не на task-done."""
        for name in ("flutter-test", "swift-test", "swift-build"):
            # Явная проверка присутствия — иначе исчезнувший гейт падает
            # KeyError'ом, и сообщение говорит про словарь вместо того, чтобы
            # сказать про пропавшее объявление.
            assert name in DEFAULT_GATES, f"гейт '{name}' исчез из реестра"
            assert "task-done" not in DEFAULT_GATES[name]["trigger"], (
                f"'{name}' повешен на task-done — это нарушает Verify-First: "
                "тяжёлый прогон обязан идти через verify с кэшем"
            )

    def test_the_new_declarations_pass_schema_validation(self):
        """AC9: иначе они не загрузятся в реестр и окажутся мёртвым текстом."""
        from stack_schema import validate_decl

        for name in ("flutter", "swift"):
            path = os.path.join(_STACKS_DIR, name, "stack.json")
            with open(path, encoding="utf-8") as fh:
                decl = json.load(fh)
            errors = validate_decl(decl, source=f"stacks/{name}/stack.json")
            assert not errors, "\n".join(errors)


def test_every_builtin_stack_decl_passes_schema_validation():
    """Страховка шире задачи: schema-валидация встроенных стеков нигде не гейтилась.

    `tausik stack lint` проверяет ТОЛЬКО пользовательские переопределения в
    .tausik/stacks/ — на встроенные объявления он не смотрит вовсе и на чистой
    машине печатает «nothing to lint». То есть stacks/_schema.json существовал,
    а встроенные декларации им никто не проверял: невалидную StackRegistry
    просто пропустила бы при загрузке.
    """
    from stack_schema import validate_decl

    problems = []
    for decl in _stack_decls():
        path = decl.pop("_path")
        problems.extend(validate_decl(decl, source=path))
    assert not problems, "\n".join(problems)
