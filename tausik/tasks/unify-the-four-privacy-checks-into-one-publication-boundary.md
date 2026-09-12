---
slug: unify-the-four-privacy-checks-into-one-publication-boundary
title: "[1.9] Свести четыре проверки приватности к одной границе публикации"
status: done
epic: release-19-renar-conformance
story: knowledge-sheds-notion-and-its-hygiene
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "publication_boundary.py (new), knowledge_export.py, project_cli_extra.py + parser flag, brain_scrubbing (read-only reuse), tests, docs, CHANGELOG."
scope_exclude: "Не восстанавливать реестр проектов, не менять схему общего хранилища, не делать redaction обязательным для локальных backup, не релизить."
relevant_files:
  - "scripts/publication_boundary.py"
  - "scripts/knowledge_export.py"
  - "scripts/project_cli_extra.py"
  - "tests/test_publication_boundary.py"
  - "tests/test_knowledge_export.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/publication_boundary.py"
  - "scripts/knowledge_export.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_parser.py"
  - "tests/test_publication_boundary.py"
  - "tests/test_knowledge_export.py"
  - "docs/en/knowledge-store.md"
  - "docs/ru/knowledge-store.md"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/unify-the-four-privacy-checks-into-one-publication-boundary.md"
  - "tausik/stories/knowledge-sheds-notion-and-its-hygiene.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T14:55:15Z"
---

## Goal

Вынесено из kb-brain-deprecate решением #221. В 1.8 снимается классификатор с РЕШЕНИЯ о публикации (это останавливает утечку); свести оставшиеся проверки в одну границу — работа архитектурная и в бюджет 1.8 не входит.

ЧЕТЫРЕ ТОЧКИ, названы карточкой-предшественницей и подтверждены разведкой:
1. маршрутизация в service_knowledge.decide (СНИМАЕТСЯ в 1.8 решением #221),
2. второй прогон того же classify внутри brain_publish_flow.assess_publish_risk,
3. scrub_inputs в brain_mcp_write.store_record,
4. гард принадлежности БД is_working_project_db в service_decide.

ПОСЛЕ 1.8 ОСТАНЕТСЯ ТРИ, и это уже лучше четырёх, но всё ещё три места, где независимо решается один вопрос. Задача — свести их к одной функции-границе.

ПОКРЫТИЕ ДОКАЗЫВАТЬ СВОЙСТВОМ, А НЕ ПЕРЕЧНЕМ (конвенция #354): всякий путь наружу проходит через единственную функцию. Перечень точек вызова устаревает молча — это в проекте уже случалось.

ГОТОВЫЙ ОБРАЗЕЦ ЕСТЬ: tests/test_notion_is_optional.py::test_no_content_reaches_notion_outside_the_scrubbed_funnel уже проверяет свойство рекурсивно по scripts/ и harness/, по трём методам записи клиента, с аллоулистом исключений С ПРИЧИНОЙ. Расширять надо его, а не писать второй.

НЕГАТИВНЫЙ СЦЕНАРИЙ ОБЯЗАТЕЛЕН: после объединения запись, которую публиковать НЕЛЬЗЯ, по-прежнему не публикуется — и тест обязан подавать вход, который прежние проверки ловили ПО ОТДЕЛЬНОСТИ, чтобы объединение не потеряло одну из них молча.

## Acceptance Criteria

AC-1: RESTATED after decision #358 — the four points named in the goal are all gone with the Notion transport (classifier routing #221, assess_publish_risk, scrub_inputs, is_working_project_db); the one path by which shared-store content still leaves this machine is tausik knowledge export, and it has a destination-shape check but no content redaction (decision on export-of-the-shared-store: deferred to 1.9). A new module scripts/publication_boundary.py is the single boundary: assert_local_destination (moved from knowledge_export, re-exported there) and redact(content, project_names, private_url_patterns) built on brain_scrubbing's four detectors, replacing each match with a typed placeholder instead of refusing. AC-2: knowledge export <dir> --redacted passes every exported field through the boundary; the manifest records redacted: true and per-detector counts; without the flag a local backup stays byte-identical (a same-machine backup must restore what it saved). AC-3 (negative, one input per detector): an email, a Windows path, a POSIX path, a private URL matching a configured pattern, and the local project's own name are each redacted on their own — so folding four checks into one loses none of them. AC-4 (negative): restoring a redacted backup over a live store leaves the live rows untouched (ON CONFLICT DO NOTHING) and a redacted backup restored into an empty store carries the placeholders, never the originals. AC-5 (property, convention #354): tests/test_publication_boundary.py walks scripts/ and harness/ by AST — every module that reads the shared store (imports knowledge_db or calls connect_knowledge_db) AND writes files or the network must import publication_boundary, with an allowlist that names each exception and its reason (the store's own writer, the mirror import, the DB module); the walk itself is asserted non-vacuous. AC-6: docs/{en,ru}/knowledge-store.md and cli.md name --redacted and the boundary; CHANGELOG EN/RU; ruff, mypy, dedupe (no new groups), signed verify.

## Plan

[{"step": "publication_boundary.py: assert_local_destination + redact \u0441 \u0442\u0438\u043f\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u043c\u0438 \u043f\u043b\u0435\u0439\u0441\u0445\u043e\u043b\u0434\u0435\u0440\u0430\u043c\u0438 \u043f\u043e\u0432\u0435\u0440\u0445 \u0447\u0435\u0442\u044b\u0440\u0451\u0445 \u0434\u0435\u0442\u0435\u043a\u0442\u043e\u0440\u043e\u0432", "done": true}, {"step": "knowledge export --redacted: \u043f\u043e\u043b\u044f \u0447\u0435\u0440\u0435\u0437 \u0433\u0440\u0430\u043d\u0438\u0446\u0443, \u043c\u0430\u043d\u0438\u0444\u0435\u0441\u0442 \u0441 redacted \u0438 \u0441\u0447\u0451\u0442\u0447\u0438\u043a\u0430\u043c\u0438", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b: \u043f\u043e \u043e\u0434\u043d\u043e\u043c\u0443 \u0432\u0445\u043e\u0434\u0443 \u043d\u0430 \u0434\u0435\u0442\u0435\u043a\u0442\u043e\u0440, \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 backup \u0431\u0430\u0439\u0442-\u0432-\u0431\u0430\u0439\u0442, restore \u043f\u043e\u0432\u0435\u0440\u0445 \u0436\u0438\u0432\u043e\u0433\u043e \u0445\u0440\u0430\u043d\u0438\u043b\u0438\u0449\u0430, property-walk \u043f\u043e scripts/ \u0438 harness/", "done": true}, {"step": "Docs EN/RU, CHANGELOG, ruff, mypy, dedupe, signed verify", "done": true}]

## Rollback

git revert одного коммита: export теряет --redacted, assert_local_destination возвращается в knowledge_export.

## Journal

- 2026-09-12T14:54:57Z [implementation] — AC verified: AC-1 ✓ publication_boundary.py is the single module; knowledge_export imports assert_local_destination and redact from it (tests/test_publication_boundary.py::test_the_exporter_itself_imports_the_boundary; the 38 export tests still green through the re-export). AC-2 ✓ test_a_redacted_backup_carries_placeholders_and_says_so (manifest redacted: true, counts) and test_a_plain_backup_stays_faithful (byte-identical content, redacted: false). AC-3 ✓ Negative: test_each_detector_redacts_on_its_own[windows-path|posix-path|email|private-url|project-name] — each fires alone with total == 1; test_a_public_url_is_not_a_private_one and test_clean_text_is_returned_untouched bound the false positives. AC-4 ✓ Negative: test_restoring_a_redacted_backup_never_overwrites_a_live_row and test_restoring_a_redacted_backup_into_an_empty_store_keeps_the_placeholders. AC-5 ✓ test_every_store_reader_that_writes_outward_passes_the_boundary (walk asserted non-vacuous: 5 store readers) + test_every_allowlist_entry_is_still_needed; a synthetic module that imports knowledge_db and calls write_text is detected (reads/writes/boundary = True/True/False, run in the journal). AC-6 ✓ docs + CHANGELOG; ruff, mypy (4 files), dedupe 290 unchanged, bootstrap --check clean, CLI help shows --redacted; signed verify below. Domain: an operator who moves a backup to another machine can now do it with placeholders instead of client names, and the manifest tells the receiver which kind of backup they hold.
- 2026-09-12T14:54:57Z [implementation] — Restated after #358 (AC-1): the four points are gone with the transport; the export was the one outward path with no content check. Implemented: scripts/publication_boundary.py (assert_local_destination moved, redact with typed placeholders over the scrubber's four detectors, imported not copied); knowledge_export(redacted=, project_names=, private_url_patterns=) with manifest redacted:+counts written LAST; CLI --redacted with _publication_blocklists (project dir name + publication.project_names / private_url_patterns); tests/test_publication_boundary.py (15 tests: one input per detector, faithful default, restore over live/empty, tree-walk property with an allowlist that must be exercised); docs knowledge-store.md EN/RU + cli.md EN/RU; CHANGELOG EN/RU. The registry union lost in the removal is replaced by the explicit config list, named in the CLI help.
