---
slug: kb-docs-consistency
title: "Сквозная согласованность документации и doc-drift гейты"
status: done
epic: release-19-renar-conformance
story: knowledge-sheds-notion-and-its-hygiene
complexity: medium
role: tech-writer
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: "Сквозная сверка S1-S6 по карте на обоих языках; проверка примеров CLI; счётчики и бейджи; покрытие doc-drift сканерами новых сущностей; отчёт в журнале и правки только там, где сверка находит расхождение."
scope_exclude: "Не переписывать страницы заново, не менять код сканеров без найденного пропуска, не релизить."
relevant_files:
  - "docs/en/knowledge-store.md"
  - "docs/ru/knowledge-store.md"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "tests/test_check_docs_hook.py"
  - "tests/test_audit_translation_drift.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "docs/en/*.md"
  - "docs/ru/*.md"
  - "docs/README.md"
  - README.md
  - README.ru.md
  - "docs/_generated/*"
  - "scripts/doc_drift_*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/kb-docs-consistency.md"
  - "tausik/stories/knowledge-sheds-notion-and-its-hygiene.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T15:20:52Z"
resolution: null
resolution_reason: null
---

## Goal

ПОСЛЕ роя: один проход, который рой сделать не может по определению — сквозная проверка. Убедиться, что сквозные утверждения из карты звучат одинаково во всех документах и на обоих языках, что нет осиротевших упоминаний Notion как обязательного шага, что примеры команд соответствуют реальному CLI, что счётчики в constants.json и бейджи README пересчитаны, а строгий doc-check зелёный. Отдельно проверить, что doc-drift сканеры не пропускают новые сущности: общая база, выгрузка, публикатор.

## Acceptance Criteria

AC-1: for each of S1-S6 the canonical wording from docs/ru/research/notion-departure-doc-map.md §3 is checked on every page the map lists for it, in both languages, and the journal records per claim: pages checked, pages fixed. AC-2 (negative): no page presents Notion as a required step — grep for imperative forms (tausik brain init, brain.enabled = true, Notion token, integration token) returns nothing outside whats-new-1.8/1.9 and research/; every 'tausik …' example in the touched pages parses against the real parser (test_cli_examples_parse plus a direct run of the parser over the examples in knowledge-store.md and configuration.md). AC-3: constants.json regenerated and gen_doc_constants --check green; README badges/counters (hooks, skills, MCP) equal the constants. AC-4: the doc-drift scanners are checked against the three new entities — shared store, export, publication boundary — and the journal states for each whether a counted claim exists in docs and, if so, which scanner binds it (or that none is needed because no number is claimed); a missing binding is fixed or filed. AC-5: full lane green except failures filed as their own tasks (renar-corpus-v11-reassessment); CHANGELOG EN/RU.

## Plan

[{"step": "S1-S6 \u0441\u0432\u0435\u0440\u043a\u0430 \u043f\u043e \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430\u043c \u043a\u0430\u0440\u0442\u044b, ru+en; \u043f\u0440\u0430\u0432\u043a\u0438 \u0440\u0430\u0441\u0445\u043e\u0436\u0434\u0435\u043d\u0438\u0439", "done": true}, {"step": "\u0418\u043c\u043f\u0435\u0440\u0430\u0442\u0438\u0432\u043d\u044b\u0435 \u0443\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f Notion; \u043f\u0440\u0438\u043c\u0435\u0440\u044b CLI \u0447\u0435\u0440\u0435\u0437 \u043f\u0430\u0440\u0441\u0435\u0440", "done": true}, {"step": "\u041a\u043e\u043d\u0441\u0442\u0430\u043d\u0442\u044b, \u0431\u0435\u0439\u0434\u0436\u0438, \u0441\u043a\u0430\u043d\u0435\u0440\u044b vs \u043d\u043e\u0432\u044b\u0435 \u0441\u0443\u0449\u043d\u043e\u0441\u0442\u0438; CHANGELOG; verify", "done": true}]

## Rollback

git revert точечных правок; отчёт — журнал.

## Journal

- 2026-09-12T15:20:20Z [implementation] — AC verified: AC-1 ✓ S1 (two stores): knowledge-store ru/en lines 7 and 176-177, memory-merge intro, README ru/en, docs/README.md section title, architecture module row (added: knowledge_db/write/read beside the boundary row) — fixed: architecture ru/en. S2 (no Notion): knowledge-store import-brain paragraph, configuration brain.local_mirror_path row, quickstart/skills/troubleshooting/environment cleared by the swarm — no fix needed. S3 (--global, nothing to configure): configuration §Publication ru/en, knowledge-store, cli.md — fixed: cli.md ru/en lacked [--global] on decide and memory add (the flag exists: parser --help shows it). S4 (export plain vs --redacted): knowledge-store, security, memory-merge, cli.md — consistent; team-state-in-git carries no export claim, none added. S5 (counters): README 146 MCP tools / 13 core skills, constants OK. S6 (scrubber = detector set of the boundary): security ru/en, memory-merge, skill-supply-chain — consistent. AC-2 ✓ Negative: grep for 'tausik brain init|brain.enabled = true|notion token|integration token|NOTION_TAUSIK_TOKEN' outside whats-new-1.8/1.9 and research/ returns nothing; 36 tausik examples in the touched pages parsed against build_parser() — one real defect found and fixed: knowledge-store ru/en showed 'knowledge export ~/dir' / 'restore ~/dir' while the parser requires --to/--from (pre-existing, not from the swarm); the other non-parses were placeholders (N, <…>) or quoted search terms. AC-3 ✓ gen_doc_constants --check OK; README counters equal constants (hooks 22 appear in the host table, skills 13, MCP 146). AC-4 ✓ shared store, export and publication boundary claim no number in any page (grep for N detectors/placeholders empty), so no scanner binding is required; the constants scanners already bind the counts those pages quote. AC-5 ✓ full lane 9982 passed; 2 failed: test_renar_standard_drift (external corpus v1.1, filed as renar-corpus-v11-reassessment) and test_release_roadmap (stale after closures; regenerated before this commit). CHANGELOG EN/RU. Domain: a newcomer following knowledge-store.md's backup example now runs a command that exists.
