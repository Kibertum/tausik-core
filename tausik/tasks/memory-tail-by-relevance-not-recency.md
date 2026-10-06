---
slug: memory-tail-by-relevance-not-recency
title: "Хвост памяти в CLAUDE.md отбирается по свежести, а не по значимости"
status: done
epic: release-1-11-3
story: release1113-hygiene-calibration
complexity: complex
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_migrations_v74.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/memory_hygiene.py"
  - "scripts/service_knowledge.py"
  - "scripts/service_knowledge_aggregates.py"
  - "scripts/project_cli_knowledge.py"
  - "scripts/project_parser.py"
  - "scripts/renar_tc_premise.py"
  - "tausik/gates.json"
  - "tests/test_memory_hygiene.py"
  - "docs/en/cli-knowledge.md"
  - "docs/ru/cli-knowledge.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T22:37:08Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#125"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Свежий агент на старте сессии видит то, что ему СЕЙЧАС нужно, а не то, что записали последним. Запись двухмесячной давности, на которую ссылались двадцать раз, обязана вытеснять вчерашнюю, которую не открыли ни разу.

## Acceptance Criteria

AC1. ПРОБЛЕМА НАЗВАНА ЧИСЛОМ, А НЕ ОЩУЩЕНИЕМ: показано, сколько записей корпуса конкурируют за пять строк хвоста на тип, и какая доля хвоста за последние N сессий состояла из записей, к которым больше ни разу не обратились.
AC2. У записи появляется СЛОЙ (у kaeru это core/hot/warm/cold/frozen). Слой меняется по накоплению — обращения, ссылки, возраст, — а не по расписанию и не вручную при каждой записи.
AC3. ПРОБНЫЙ ПРОГОН ОБЯЗАТЕЛЕН. Отдельная команда показывает, что следующий проход сделает и почему, НИЧЕГО не меняя. У kaeru это hygiene <initiative>, и рекомендация прямая: сначала прогнать на хранилище, которое дорого, и только потом включать.
AC4. ЛЮБОЕ ПЕРЕМЕЩЕНИЕ ОБРАТИМО ОДНОЙ КОМАНДОЙ и ничего не удаляет. Понижение слоя — не удаление; запись остаётся достижимой по прямому запросу.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: запись, помеченная как обязательная к показу, не понижается автоматически НИКОГДА. Иначе первая же гигиена уронит из хвоста то, ради чего он существует.
AC6. НЕГАТИВНЫЙ СЦЕНАРИЙ: при пустом корпусе и при корпусе из одной записи хвост не ломается и не даёт пустых заголовков. Тот же класс дефекта уже ловился в mcp-update-claudemd-erases-the-memory-tail.
AC7. Механизм включается ЯВНО и по умолчанию выключен, пока не набрано доказательство на нашем корпусе. У kaeru он тоже opt-in, и это осознанная осторожность, а не недоделка.

## Plan

## Rollback

git revert: отбор возвращается к последним N по типу; слои остаются в БД неиспользованными и не мешают

## Journal

- 2026-09-29T21:19:32Z [implementation] — Taken out of 1.10 (my own inclusion error, session #279): AC1 needs per-record access counts that do not exist (brain_events has no memory id), AC7 ships it off by default, and it does not shrink the tail — so it pays nothing to 1.10 token economy. Prerequisite: record memory hits per id. Back to deferred for 1.11.
- 2026-10-06T22:36:33Z [implementation] — NO-DEAD-END: red verify runs #3563-#3566 were ordinary gate iterations, not failed approaches — #3563 ruff F541 (f-string without placeholder), #3564 ruff S110 + filesize cap tripped by three registry surfaces (fixed by noqa S110 and TEMPORARY gates.json exempt_files entries naming the retainer task split-the-three-registry-surfaces-over-the-line, filed as planning), #3565 RUF100 unused noqa, #3566 renar_tc_premise CLASSES_AT_DECLARATION gained memory_hygiene_snapshots (new artifact class declared NOT-TC with reason). #3567 exit=0.
- 2026-10-06T22:36:48Z [implementation] — AC-1 (problem named by number): ✓ 18 tail lines vs 895 active records (~50:1 per line; conventions 216 for 5 = 43:1); 60 committed CLAUDE.md tails mined — oldest and newest snapshot share ZERO records (full turnover on recency), 26 of 158 distinct tail records (16.5%) appeared exactly once. AC-2 (layer by accumulation): ✓ planned_layer — core: pinned or >=20 reads; hot >=8; warm >=2; cold: 1 read or fresh; frozen: 0 reads and >90d — never schedule, never manual per record. AC-3 (dry-run mandatory): ✓ report_lines writes nothing; live run: 'corpus: 895 active record(s), planned moves: 895 — cold: 708, frozen: 187'; tests/test_memory_hygiene.py::TestHygieneLifecycle::test_report_writes_nothing. AC-4 (one-command revert, deletes nothing): ✓ memory_hygiene_snapshots + revert_last; test_apply_then_revert_restores. AC-5 NEGATIVE (pinned never demoted): ✓ apply skips pinned entirely; test_pinned_is_never_touched_by_apply; pin/unpin CLI. AC-6 NEGATIVE (empty/single corpus): ✓ test_empty_corpus_tail_is_empty_and_report_survives; test_single_record_corpus_keeps_one_heading_one_line (no empty headings — the mcp-update-claudemd class). AC-7 (explicit opt-in, default off): ✓ tail_by_relevance_enabled reads config.json, default false; test_flag_defaults_off + test_default_tail_is_recency (legacy order byte-identical); flag-on path test_opt_in_flag_changes_the_aggregate_tail. All: ✓ tests/test_memory_hygiene.py (20 passed), ✓ live dry-run after bootstrap redeploy, ✓ green verification_run #3567. Domain: dry-run inspected on the production corpus; hit recording live from this session (every memory show bumps); activation deliberately left to the owner per kaeru guidance — counts start at zero today. Verify #3567 exit=0, handle presented.
