---
slug: qg0-does-not-refuse-work-for-session-time-or-capacity
title: "QG-0 перестаёт отказывать в старте задачи по времени сессии и ёмкости вызовов — это не Quality Gates"
status: done
epic: release-110-deferred-from-19
story: release110-sessions-are-not-gates
complexity: complex
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_recording.py"
  - "scripts/service_task.py"
  - "scripts/gate_qg0_check.py"
  - "scripts/service_session_metrics.py"
  - "scripts/hooks/session_cleanup_check.py"
  - "scripts/project_parser_task.py"
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_session_capacity.py"
  - "tests/test_med_findings_fix.py"
  - "tests/test_session_two_halves.py"
  - "tests/test_bootstrap_generate.py"
  - "tests/test_session_signal_not_gate.py"
  - "tests/test_attempts_counter.py"
  - "tausik/gates.json"
  - "docs/ru/agent-contract.md"
  - "docs/ru/sessions.md"
  - "docs/en/sessions.md"
  - "docs/ru/session-active-time.md"
  - "docs/en/session-active-time.md"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/en/senar-compliance-matrix.md"
  - CLAUDE.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/gate_qg0_check.py"
  - "scripts/service_gates.py"
  - "scripts/service_recording.py"
  - "scripts/service_task.py"
  - "scripts/service_session*.py"
  - "scripts/status_view.py"
  - "scripts/hooks/session_cleanup_check.py"
  - "scripts/project_parser*.py"
  - "scripts/project_cli*.py"
  - "harness/claude/mcp/project/*.py"
  - "bootstrap/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
  - CLAUDE.md
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T15:47:57Z"
---

## Goal

Сегодня check_qg0_start отказывает в старте задачи в двух случаях, не имеющих отношения к контексту задачи: (а) активное время сессии > 180 минут (session_check_duration_fn, «Use /end or session extend»), (б) бюджет задачи > остатка ёмкости 200 вызовов (check_session_capacity, «end the shift and start a fresh session», обход — --force). Оба отказа — про контекстное окно агента, а не про состояние записи задачи, которую QG-0 обязан проверять (SENAR 1.5 §8.1: вердикт QG-0 — о записи задачи и ни о чём другом; §8.6(a): у гейта объявленный предотвращаемый эффект, у «времени» и «ёмкости» его нет). Замер: за 70 смен #196–#265 ни одна не дошла до 180 активных минут, продление session extend не вызывалось ни разу (0 событий), а ёмкость упомянута в итогах 13 смен и породила серию перезапусков #252–#260. Цель: QG-0 проверяет только задачу; время и ёмкость становятся советом в выводе task start, status и Stop-хука с измеренными числами, но никогда — отказом. Это и есть запись пересмотра capability-dependent положения по SENAR 1.5 §10.13 (смена поколения моделей: агенты работают часами автономно).

## Acceptance Criteria

1. Воспроизведено ДО правки тестом: сессия с активным временем выше лимита → task start отказывает; задача с budget выше остатка → task start отказывает. После правки оба сценария стартуют задачу, а в выводе есть строка-совет с числами (активные минуты / вызовы этой сессии).
2. НЕГАТИВНЫЙ: QG-0 по-прежнему отказывает без goal, без AC, без негативного сценария, без scope/rollback для medium/complex — существующие тесты gate_qg0_check не изменены и зелены.
3. НЕГАТИВНЫЙ: флаг --force у task start снят; его передача — явный отказ с текстом «флаг отозван: ёмкость больше не гейт», а не тихое игнорирование; audit-событие обхода ёмкости больше не пишется, потому что обходить нечего.
4. check_session_capacity остаётся источником чисел для совета: «нет открытой сессии» по-прежнему ЯВНОЕ состояние в тексте совета (решение #223), а не молчание.
5. Совет называет основание порога ссылкой на документ, где основание записано (SENAR 1.5 §9.4(c)); числа порогов в тексте не дублируются вручную — берутся из конфига.
6. Документы: docs/ru и docs/en — agent-contract (строка Rule 9.2), sessions.md, session-active-time.md, cli.md (task start), senar-compliance-matrix (строки 9.2/9.3 переезжают в раздел «за пределами Core»); CLAUDE.md core и шаблон bootstrap (HARD_CONSTRAINTS) — строка «Лимит сессии 180 мин ACTIVE» заменена сигнальной формулировкой; тест на присутствие обеих формулировок в обоих местах.
7. Записан итог пересмотра по §10.13 (решение с датой и основанием: замер 70 смен, 0 достижений лимита, серия перезапусков ради ёмкости) и упомянут в CHANGELOG (EN+RU).
8. Scoped verify зелёный по relevant_files; полная лента — в CI.

## Plan

## Rollback

git revert коммита; схема БД не меняется; --force возвращается тем же revert'ом.

## Journal

- 2026-09-23T14:25:16Z [implementation] — Замер ДО: check_qg0_start отказывал по session_check_duration_fn (QG-0 Start Gate: ... Use /end), service_recording.check_session_capacity отказывал по бюджету и без сессии, --force писал capacity_force_start; MCP task_start флага не имел. Правка: session_capacity_advisory возвращает совет (не raise), QG-0 пропускает превышение как SESSION: предупреждение, --force отвечает отказом с текстом «retired» (task start и unblock), audit-событие удалено, Stop-хук и session_overrun_warning называют порог советом с ссылкой на session-active-time.md, парсер помечает флаг отозванным. Документы: agent-contract, sessions (ru/en), session-active-time (ru/en, раздел «Основание порога» с замером 70 смен), cli (ru/en), матрица (ru/en), CLAUDE.md, bootstrap_templates. Тесты: test_session_capacity, test_med_findings_fix, test_session_two_halves, test_bootstrap_generate переписаны на совет; новый tests/test_session_signal_not_gate.py (10 тестов, 2 негативных). 170 тестов зелёные, ruff check/format чисты.
- 2026-09-23T14:34:37Z [implementation] — verify run #2672 green (ruff, scoped pytest 122 files); tests/test_session_signal_not_gate.py 10 tests incl. 2 negative; decision #380; CHANGELOG EN+RU
- 2026-09-23T14:34:37Z [implementation] — ДОКАЗАТЕЛЬСТВА ПО КРИТЕРИЯМ. AC1: воспроизведено тестами до правки (test_session_capacity::test_blocks_when_overshoot, test_med_findings_fix::TestForceFlag падали с ServiceError match=capacity); после правки test_session_signal_not_gate::TestTheService::test_over_capacity_starts_and_says_so и ::test_no_session_starts_and_names_the_unmeasured_capacity — задача стартует, строка совета с числами. AC2 НЕГАТИВ: test_session_signal_not_gate::TestTheGateFunction::test_the_task_record_is_still_gated (отказ без goal при наличии session warning), существующие тесты gate_qg0 не тронуты. AC3 НЕГАТИВ: ::test_force_is_refused_with_the_reason_and_changes_nothing и ::test_unblock_force_is_refused_too (текст retired, статус не меняется), ::test_the_capacity_force_event_is_never_written. AC4: советы называют «no session is open» и tausik session start (test_session_two_halves::test_capacity_signal_names_the_absent_session). AC5: совет ссылается на docs/ru/session-active-time.md (assert в test_over_capacity_starts_and_says_so); порог берётся из конфига (_session_max_min в Stop-хуке, session_max_minutes в status). AC6: agent-contract, sessions ru/en, session-active-time ru/en, cli ru/en, матрица ru/en, CLAUDE.md, bootstrap_templates; test_session_signal_not_gate::TestTheRuleIsStatedInBothPlaces держит фразу в CLAUDE.md и HARD_CONSTRAINTS; test_bootstrap_generate маркеры обновлены. AC7: решение #380 (пересмотр по §10.13, дата и основание), CHANGELOG EN+RU записи. AC8: scoped verify run #2672 зелёный (ruff PASS, pytest PASS 122 файлов), handle 2672.c94cf1c828bf0656954155bc9749db68; полная лента — CI.
- 2026-09-23T14:34:50Z [implementation] — AC verified: 1 — tests/test_session_signal_not_gate.py::TestTheService (over-capacity and no-session starts print the advisory), verify #2672 green; 2 — TestTheGateFunction::test_the_task_record_is_still_gated (negative: missing goal still refused with a session warning present); 3 — test_force_is_refused_with_the_reason_and_changes_nothing, test_unblock_force_is_refused_too, test_the_capacity_force_event_is_never_written (negative: retired flag refused, no capacity_force_start); 4 — test_session_two_halves.py::test_capacity_signal_names_the_absent_session (absent session named, tausik session start); 5 — advisory names docs/ru/session-active-time.md (asserted), thresholds read from config (_session_max_min, session_max_minutes); 6 — docs ru/en (agent-contract, sessions, session-active-time, cli, matrix), CLAUDE.md and bootstrap_templates carry the rule, TestTheRuleIsStatedInBothPlaces + test_bootstrap_generate markers; 7 — decision #380 records the §10.13 review with date and basis, CHANGELOG EN+RU entries; 8 — scoped verify run #2672 passed (ruff PASS, pytest PASS over 122 mapped files), full lane in CI.
- 2026-09-23T14:34:50Z [implementation] — verify run #2672 green (ruff, scoped pytest 122 files); tests/test_session_signal_not_gate.py 10 tests incl. 2 negative; decision #380; CHANGELOG EN+RU
- 2026-09-23T15:47:51Z [implementation] — verify run #2674 green (ruff, scoped pytest); tests/test_session_signal_not_gate.py incl. negatives; decision #380; CHANGELOG EN+RU
- 2026-09-23T15:47:51Z [implementation] — Гейты закрытия первой попытки: filesize (service_task.py 513 → 500 — константа FORCE_RETIRED перенесена в service_recording; agent-contract.md 515 → 485 — дубль матрицы SENAR заменён ссылкой на senar-compliance-matrix.md), test_dedupe (три копии одной формы теста → одна, в test_session_signal_not_gate; храповик опущен до замера 289/684), bootstrap_drift (bootstrap --ide all, --check чист), CLAUDE.md статика 4307 → под 4096. Verify run #2674 зелёный.
