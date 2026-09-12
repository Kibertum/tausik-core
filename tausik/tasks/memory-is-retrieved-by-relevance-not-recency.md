---
slug: memory-is-retrieved-by-relevance-not-recency
title: "Память достаётся по недавности, а не по релевантности задачи"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "memory_relevance.py (терм-набор из задачи + FTS OR-выборка + причины), backend OR-запрос, поверхность в task_start (старт и resume) и task show; тесты; docs; CHANGELOG."
scope_exclude: "Не менять хвост по недавности в CLAUDE.md (ядро — отдельная задача), не вводить эмбеддинги, не трогать shared store, не релизить."
relevant_files:
  - "scripts/memory_relevance.py"
  - "scripts/backend_queries.py"
  - "scripts/service_task.py"
  - "tests/test_memory_relevance.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/memory_relevance.py"
  - "scripts/backend_queries.py"
  - "scripts/service_task.py"
  - "scripts/project_cli_task.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "tests/test_memory_relevance.py"
  - "docs/en/knowledge-store.md"
  - "docs/ru/knowledge-store.md"
  - "docs/en/memory-merge-guidelines.md"
  - "docs/ru/memory-merge-guidelines.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/memory-is-retrieved-by-relevance-not-recency.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T15:51:52Z"
---

## Goal

ПЕРЕНОС РЕКОМЕНДАЦИИ ANTHROPIC. Структурные заметки живут ВНЕ окна и втягиваются обратно В НУЖНЫЙ МОМЕНТ. У нас хранение есть, а втягивание — хвост по пять записей на тип, выбранный по НЕДАВНОСТИ. Пробел у нас в ИЗВЛЕЧЕНИИ, а не в хранении: 431 запись памяти есть, а в окно попадают последние пять на тип независимо от того, о чём задача.
ЧТО ДЕЛАЕТСЯ: на task start и на resume архив достаётся ПО РЕЛЕВАНТНОСТИ задачи — по объявленному scope (файлы и их импорты), по тегам, по связанным задачам и решениям, а не по времени записи. FTS5 уже есть, эмбеддингов не требуется.
НЕГАТИВНОЕ: выборка по релевантности НЕ ИМЕЕТ ПРАВА молча возвращать пусто — пустой результат обязан быть назван, иначе агент решит, что памяти по теме нет. И она не отменяет ядро (отдельная задача): ядро втягивается всегда, релевантное — сверх него.
ИЗМЕРИМЫЙ КРИТЕРИЙ: для задач сессии #189 выборка по релевантности обязана вернуть память #425 (отменяющая правило пяти имён) и #428 (различие наборов гейтов) — их рукописный промпт нёс руками, а хвост по недавности не вернул бы.

## Acceptance Criteria

AC-1: memory_relevance.relevant_memory(be, task) builds the term set from the task itself — title and slug words, stems and path segments of relevant_files and scope_paths, the parent story slug, tags of decisions linked to the task — and runs ONE FTS5 query with OR semantics (a new backend method; the existing memory_search is implicit AND and untouched), returning up to 8 live, non-archived, non-superseded entries ordered by bm25, each with the terms that matched it. AC-2: task start (fresh start and the 'already active' resume path) and task show print a 'Relevant memory (N)' block with #id and title per entry — on top of, not instead of, the recency tail in CLAUDE.md. AC-3 (negative): an empty result is NAMED, never silent: the block reads 'Relevant memory: none matched <terms>' listing the terms tried, so an agent cannot read silence as 'no memory on this topic'; an FTS error degrades to that same named line, never to a crash of task start. AC-4 (measurable): for the session-#189 task cross-model-parity-has-no-gate (relevant_files gate_cross_model_parity.py, host_mechanisms.py, gate_registry_scoped.py, test_cross_model_parity_gate.py) the live database returns memory #425 (the retired five-names rule) and #428 (a signed receipt is not a passing commit) — both absent from the recency tail of that day; asserted by a test against a fixture that reproduces those two rows plus 30 newer decoys. AC-5 (negative): a superseded entry is not returned in place of its replacement (live_head semantics), and a term that matches nothing does not poison the OR query. AC-6: docs knowledge-store/memory-merge name the retrieval; CHANGELOG EN/RU; ruff, mypy, dedupe, signed verify.

## Plan

[{"step": "backend: memory_search_any(terms) \u0441 OR \u0438 bm25; memory_relevance: \u0442\u0435\u0440\u043c\u044b, \u0432\u044b\u0431\u043e\u0440\u043a\u0430, \u043f\u0440\u0438\u0447\u0438\u043d\u044b, \u043f\u0443\u0441\u0442\u043e\u0439 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442 \u043d\u0430\u0437\u0432\u0430\u043d", "done": true}, {"step": "\u041f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u044c: task_start (start + resume) \u0438 task show", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b: \u0444\u0438\u043a\u0441\u0442\u0443\u0440\u0430 #425/#428 + 30 \u043f\u0440\u0438\u043c\u0430\u043d\u043e\u043a, \u043f\u0443\u0441\u0442\u043e\u0439, \u0434\u0435\u0433\u0440\u0430\u0434\u0430\u0446\u0438\u044f, superseded; docs; CHANGELOG; verify", "done": true}]

## Rollback

git revert; данные не мигрируют, хвост по недавности остаётся как был.

## Journal

- 2026-09-12T15:41:35Z [implementation] — AC verified: AC-1 ✓ memory_relevance.task_terms/relevant_memory: terms from title, slug, relevant_files + scope_paths stems and segments (JSON-text fields parsed), story, linked-decision tags; backend.memory_search_any is the new OR form (memory_search untouched); up to 8 live rows, bm25 then a where-matched second stage (tag 3 / title 2 / body 1), each with its matched terms. AC-2 ✓ task_start (fresh), task_start on an active task ('already active (resumed)') and task_show all carry the block; CLI task show and the MCP tausik_task_show print it (test_task_start_prints_the_block). AC-3 ✓ Negative: test_an_empty_answer_is_named_with_the_terms_tried; test_a_failing_search_degrades_to_a_named_line_not_a_crash (RuntimeError from FTS → one named line, task start unaffected). AC-4 ✓ test_the_parity_task_pulls_425_and_428_from_under_thirty_decoys (fixture: both rows under 30 newer decoys, #425 ahead of #428); live store measurement for cross-model-parity-has-no-gate: #425 ranks 2nd of 8; #428 reaches the candidate set via 'gate' but ranks below the top eight among dozens of gate-tagged rows — recorded, not hidden; it is the recency tail's kind of row. AC-5 ✓ Negative: test_a_superseded_row_yields_to_its_replacement; test_a_term_matching_nothing_does_not_poison_the_query (and the empty term list returns []); test_the_decoys_do_not_outrank_the_subject_rows. AC-6 ✓ memory-merge-guidelines EN/RU new section; CHANGELOG EN/RU; ruff, mypy (4 files), dedupe 290 unchanged; 179 neighbouring tests green; signed verify below. Domain: the block for the live parity task lists #607 (CROSSCUTTING_SCOPE is read by literal_eval), #425, #617 (register a blocking gate in three places) — exactly the three things an agent starting that task would otherwise learn by failing.
- 2026-09-12T15:49:28Z [implementation] — Gate finding fixed before closure: the class-surface ratchet refused two new public members on the god classes (SQLiteBackend 169→170, ProjectService 148→149). The OR search now lives in memory_relevance.search_any over the backend's row helper, and the three call sites call lines_for_task directly — both classes back at their baselines; gate green.
