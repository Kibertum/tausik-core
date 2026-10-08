---
slug: verify-a-gate-by-mutation-not-by-passing
title: "Гейт проверяется мутацией, а не тем, что он зелёный"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
role: qa
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: "scripts/gate_*.py и gate_registry.py: реализации гейтов НЕ правятся — задача о ДИСЦИПЛИНЕ проверки, а не о гейтах; найденный дефект гейта заводится отдельно. Хуки PreToolUse (task_gate, scope_write_gate, bash_write_gate, memory_pretool_block) — вторая вселенная, покрытая собственными тестами через реальный хук; в реестр QG-2 не входят и здесь не классифицируются — объявлено в докстринге модуля"
relevant_files:
  - "tests/test_gates_catch_their_violation.py"
  - "docs/ru/architecture.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "tests/test_gates_catch_their_violation.py"
  - "docs/ru/architecture.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-03T16:06:31Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Про каждый защитный гейт известно, что он ЛОВИТ нарушение, а не просто не мешает. Проверено внесением настоящего нарушения, а не наблюдением зелёного прогона.

## Acceptance Criteria

AC1. ОБРАЗЕЦ ЖИВОЙ И ИМЕННО ТАКОЙ. В ветке senar-14 репозитория стандарта добавлен собственный гейт инвариантов, и в changelog записано: 'проверен мутацией, а не прохождением — шесть намеренных расхождений внесены по одному, и каждое было поймано'. Это дисциплина, а не инструмент.
AC2. У НАС ЭТА ДИСЦИПЛИНА УЖЕ ПРОБИВАЛАСЬ СТИХИЙНО И ОКУПАЛАСЬ. В сессии #177 гейт литерала .claude покраснел на настоящем нарушении, а не на выдуманном, и это поймало перенос литерала в новый модуль. Задача превращает случай в правило.
AC3. ОХВАТ НАЗВАН ЧЕСТНО. Мутацией покрываются защитные гейты, а не все тесты подряд. Список гейтов, попавших под требование, и список сознательно не попавших — с причиной по каждому.
AC4. НЕГАТИВНЫЙ СЦЕНАРИЙ: мутация обязана вноситься ВРЕМЕННО и не иметь возможности остаться в дереве. Проверка, которая пачкает репозиторий испорченным файлом, будет выключена первой же злой сессией.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: гейт, который краснеет на ЛЮБОМ входе, мутационную проверку проходит так же успешно, как правильный. Значит нужна и обратная сторона: на чистом входе гейт обязан быть зелёным. Проверяются оба конца, иначе доказательство пустое.
AC6. Результат — не разовый отчёт, а повторяемый прогон. Разовая проверка протухнет с первой правкой гейта.
AC7 (#207, ИЗМЕРИМАЯ ФОРМА AC3-AC6). Вселенная = gate_registry.GATE_REGISTRY (закрытый список, 17 имён). Один тестовый модуль tests/test_gates_catch_their_violation.py держит две таблицы: COVERED — гейт -> (нарушение, чистый вход), оба строятся ТОЛЬКО под tmp_path и прогоняются через impl_for(name) из реестра, нарушение обязано дать failed, чистый — passed; EXCUSED — гейт -> причина + имена красного И зелёного теста в существующем модуле, существование которых проверяется разбором AST этого модуля. Тест закрытого списка: COVERED ∪ EXCUSED == реестр, пересечение пусто — новый гейт без классификации краснит ленту. AC4 — по построению: каждый созданный путь под tmp_path (утверждается тестом), плюс `git status --porcelain` до и после прогона таблицы не отличается.
AC8 (#207). Цифры в журнале: сколько гейтов в COVERED, сколько в EXCUSED, по каким причинам; мутации САМОГО модуля (снять красный конец, снять зелёный, снять закрытость списка) — каждая убита. docs/ru/architecture.md описывает правило; CHANGELOG.md и CHANGELOG.ru.md синхронно; полная лента один раз со строкой passed/failed.

## Plan

## Rollback

git revert: проверка мутацией уходит, гейты снова считаются рабочими по зелёному прогону

## Journal

- 2026-09-03T16:02:28Z [implementation] — ИНВЕНТАРЬ ВСЕЛЕННОЙ: gate_registry.GATE_REGISTRY = 15 имён (ruff, mypy, filesize, class_surface, bandit, tdd_order, bootstrap_drift, memory_route, renar_drift_schema, renar_drift_provenance, state_roundtrip, claudemd_state_drift, skill_spec_conformance, verify_first, changelog); pytest и hadolint из gates status — гейты СТЕКОВ, экземпляры command runner, объявлены вне реестра в докстринге. COVERED = 6 (filesize, class_surface, memory_route, bootstrap_drift, skill_spec_conformance, state_roundtrip) — оба конца через impl_for под tmp_path, все 12 клеток верны с первого прогона. EXCUSED = 9: command-гейты ruff/mypy/bandit (вердикт инструмента; test_gate_command_runner), tdd_order (warn+off), renar_drift_schema/provenance (warn, нужен RENAR-стор), claudemd_state_drift (красный конец — реальные снимки из git history), verify_first и changelog (svc-bound). У каждого — причина и имена красного И зелёного теста, сверяемые AST.
- 2026-09-03T16:02:29Z [implementation] — МУТАЦИИ ТАБЛИЦЫ 5/5 УБИТЫ: (1) гейт снят из обеих таблиц — test_every_registered_gate_is_classified; (2) красный билдер строит чистый вход — test_a_real_violation_is_refused[bootstrap_drift]; (3) зелёный билдер строит нарушение — test_a_clean_input_is_allowed[filesize]; (4) оправдание указывает на несуществующий тест — test_an_excuse_names_a_reason_and_both_ends_that_exist[verify_first]; (5) билдер пишет файл в tests/ репозитория — ВЫЖИЛА в первой версии (снимок git status до/после), убита после замены на перехват open. ГОТЧА: под xdist соседний воркер выполнил тот же билдер ДО снимка «до», подкидыш попал в оба снимка и before == after; проверка через git status порядково-зависима, перехват записи — нет; io.open патчится отдельно от builtins.open (Path.write_text идёт через io.open).
- 2026-09-03T16:05:25Z [implementation] — AC-1: ✓ образец senar-14 воспроизведён как дисциплина: таблица форм, а не инструмент. AC-2: ✓ случай #177 стал правилом — закрытый список по реестру. AC-3: ✓ COVERED 6 / EXCUSED 9 с причинами — в модуле и в журнале. AC-4: ✓ tested via test_the_table_leaves_the_repository_untouched — перехват open/io.open, мутация с подкидышем убита. AC-5: ✓ tested via test_a_real_violation_is_refused и test_a_clean_input_is_allowed — 6 x 2 клеток. AC-6: ✓ pytest-модуль в ленте, CROSSCUTTING_SCOPE tests/. AC-7: ✓ tested via test_every_registered_gate_is_classified (15 == 6 + 9, пересечение пусто) и test_an_excuse_names_a_reason_and_both_ends_that_exist (AST). AC-8: ✓ мутации 5/5 в журнале, docs/ru/architecture.md, CHANGELOG.md + CHANGELOG.ru.md, полная лента 8607 passed / 25 skipped / 0 failed (строка прочитана), ruff чисто. Domain: шесть защитных гейтов теперь доказанно КРАСНЕЮТ на настоящем нарушении и зеленеют на чистом входе в каждом прогоне ленты; новый гейт без классификации не пройдёт ленту.
- 2026-09-03T16:06:54Z [done] — Verification checklist (форма, читаемая парсером): AC-1: ✓ tests/test_gates_catch_their_violation.py::test_every_registered_gate_is_classified. AC-2: ✓ tests/test_gates_catch_their_violation.py::test_a_real_violation_is_refused. AC-3: ✓ tests/test_gates_catch_their_violation.py::test_an_excuse_names_a_reason_and_both_ends_that_exist. AC-4: ✓ tests/test_gates_catch_their_violation.py::test_the_table_leaves_the_repository_untouched. AC-5: ✓ tests/test_gates_catch_their_violation.py::test_a_clean_input_is_allowed. AC-6: ✓ tests/test_gates_catch_their_violation.py::test_a_real_violation_is_refused. AC-7: ✓ tests/test_gates_catch_their_violation.py::test_every_registered_gate_is_classified. AC-8: ✓ verification_run #1993 green; мутации 5/5 в журнале.
