---
slug: mypy-ten-preexisting-errors-nobody-owns
title: "mypy держит 10 преэкзистующих ошибок, и каждое закрытие пишет в evidence «все преэкзистующие» вместо того, чтобы их убрать"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 18
defect_of: null
scope: "tests/ (новый slow-тест mypy scripts/ == 0). Код: 10 ошибок уже исправлены (mypy-residual-argtype-untangle этого батча) — премиса устарела, подтвердить замером."
scope_exclude: "Не менять mypy-конфиг/overrides без нужды; не добавлять per-module ignore (цель — ноль, не подавление)"
relevant_files:
  - "tests/test_mypy_clean.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T23:22:31Z"
---

## Goal

Замер сессии #135: `python -m mypy scripts/gate_runner.py scripts/gate_command_runner.py` -> Found 10 errors in 7 files. Ни одна не в проверяемых модулях — mypy тянет их по импортам: supply_eol.py:62, skill_deps.py:45+48, gate_registry.py:304+328, verify_envelope.py:113, gate_post_scope.py:118, gate_bootstrap_drift.py:53, service_gates.py:140.

Почему это надо закрыть, а не терпеть. Evidence закрытий уже второй релиз подряд содержит формулу «mypy N ошибок — все преэкзистующие, счёт не вырос». Это работающий приём ровно до первого раза, когда счёт не вырос ПОТОМУ ЧТО одна новая ошибка совпала с одной исправленной. Порог «не вырос» — это не порог, это отсутствие порога; фреймворк, который учит доказывать факт вместо формы, не может держать у себя проверку, читающую динамику вместо состояния.

Типы ошибок разнородны: шесть штук no-any-return (лечится аннотацией или cast на границе), одна import-not-found на bootstrap_venv (тот же класс, что уже решён для memory_markers через override в pyproject), две arg-type — настоящие расхождения сигнатур (gate_post_scope передаёт None туда, где объявлен int; service_gates передаёт Callable[[], int] туда, где Callable[[], None]). Последние две могут оказаться настоящими дефектами, а не шумом типизации — начинать с них.

Ожидаемый результат: mypy по scripts/ чист, и в CI/гейтах появляется проверка НУЛЯ, а не «счёт не вырос».

## Acceptance Criteria

AC1. Премиса проверена замером: `python -m mypy scripts/gate_runner.py scripts/gate_command_runner.py` → Success (было Found 10 errors); `python -m mypy scripts/` → Success 280 files. 10 ошибок уже устранены (mypy-residual-argtype-untangle), не подавлены.
AC2. Проверка НУЛЯ (не «счёт не вырос») закреплена executable-тестом: test_scripts_tree_is_mypy_clean запускает mypy по scripts/ и требует returncode==0, чтобы преэкзистующая ошибка в НЕтронутом файле не могла спрятаться (mypy-гейт скоупится по файлам задачи).
AC3. НЕГАТИВ/устойчивость: тест пропускается (skip), если mypy не установлен (не ложное падение). Осознанно НЕ помечен slow — zero-check, который живёт только в opt-in slow-лейне, это та самая динамика-которую-никто-не-мерит; ~3-4с в дефолтном полном прогоне приемлемо, чтобы регрессия ловилась сразу.
AC4. Тест зелёный сейчас (mypy scripts/ чист); при реинтродукции ошибки типа returncode!=0 → assert падает с выводом mypy (by construction).
AC5. Формула evidence «mypy N ошибок — все преэкзистующие» больше не нужна: репо доказуемо на нуле, и это факт (тест), а не динамика.

## Plan

## Rollback

git revert; изменение — новый тест (аддитивно). Откат убирает repo-wide zero-check, но код остаётся mypy-clean.

## Journal

- 2026-07-26T23:22:30Z [implementation] — AC-1: ✓ Премиса устарела/исправлена — замер: `mypy scripts/gate_runner.py scripts/gate_command_runner.py` → Success (было 10 errors); `mypy scripts/` → Success 280 files. 10 ошибок устранены (mypy-residual-argtype-untangle этого батча), НЕ подавлены override. AC-2: ✓ Zero-check закреплён — tests/test_mypy_clean.py::test_scripts_tree_is_mypy_clean (subprocess mypy scripts/, assert returncode==0; ловит преэкзистующую ошибку в НЕтронутом файле, которую per-file mypy-гейт пропускает). verification_run #1467 (свой зелёный) scoped pytest PASS (1 passed). AC-3: ✓ skipif(not mypy) — не ложное падение без mypy; осознанно НЕ slow (иначе zero-check жил бы в opt-in лейне = та самая динамика). AC-4: ✓ by construction: returncode!=0 → assert падает с выводом mypy; сейчас зелёный т.к. mypy чист. AC-5: ✓ формула «все преэкзистующие» заменена фактом (тест на ноль). Domain: порог «не вырос» — отсутствие порога (проходит когда новая ошибка совпала с исправленной); теперь состояние=0 проверяется, не динамика — класс проекта «доказывай факт, не форму». Test-only guard, фикс уже в CHANGELOG (mypy-residual-argtype-untangle) → no_changelog.
