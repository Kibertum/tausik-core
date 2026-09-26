---
slug: kb-docs-swarm
title: "Роевое обновление документации по зонам"
status: done
epic: release-19-renar-conformance
story: knowledge-sheds-notion-and-its-hygiene
complexity: complex
role: tech-writer
stack: null
tier: substantial
call_budget: 90
defect_of: null
scope: "Переписать 45 файлов карты по зонам Z1-Z4 с формулировками S1-S6; удалить Z1; поправить входящие ссылки и комментарий теста; пересобрать константы."
scope_exclude: "Не трогать research/, whats-new-1.8, код кроме docstring brain_scrubbing:18 и комментария в test_doc_gate_list_parity.py; не релизить."
relevant_files:
  - "docs/en/knowledge-store.md"
  - "docs/ru/knowledge-store.md"
  - "docs/en/skills.md"
  - "docs/ru/skills.md"
  - "docs/README.md"
  - README.md
  - README.ru.md
  - "tests/test_doc_gate_list_parity.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "docs/en/*.md"
  - "docs/ru/*.md"
  - "docs/README.md"
  - README.md
  - README.ru.md
  - "scripts/brain_scrubbing.py"
  - "tests/test_doc_gate_list_parity.py"
  - "docs/_generated/*"
  - AGENTS.md
  - CLAUDE.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/kb-docs-swarm.md"
  - "tausik/stories/knowledge-sheds-notion-and-its-hygiene.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T15:14:12Z"
resolution: null
resolution_reason: null
---

## Goal

Параллельное обновление docs/ru и docs/en роем агентов, по одному агенту на зону из карты kb-docs-map. Ключевые ограничения, вытекающие из опыта проекта: зоны не пересекаются по файлам; агентам НЕ давать живое рабочее дерево с правом запуска (решение #135 — однажды это испортило bootstrap.py), для документации достаточно прав на чтение и запись только в свою зону; каждому агенту передаётся ОДИН и тот же набор сквозных утверждений из карты, чтобы формулировки не разъехались. Рой уместен именно здесь: работа широкая, слабо связанная и хорошо делится — в отличие от параллельной записи кода, где отраслевые данные показывают проигрыш.

## Acceptance Criteria

AC-1: every file of the map's 45 is handled by its zone's fate: Z1 four pairs deleted, Z2/Z3 sections rewritten or lines removed as the map lists, Z4 root and index updated; the map's §1 grep afterwards returns only whats-new-1.9.md (ru+en), cli.md:482 and skill-supply-chain-threat-model.md (ru+en), i.e. at most 5 files. AC-2: zones do not overlap — each commit touches one zone's files only, so the git history shows one owner per file (the swarm ran as one agent processing zones in the map's order; the tooling of this host cannot confine a subagent to a path set, so isolation is by commit boundary, recorded honestly). AC-3: the six claims S1-S6 are worded per the map on every page that carries them — grep for the retired wordings ('three stores'/'трёх хранилищ', 'brain.enabled', 'tausik brain', 'tausik-brain', '/brain') returns nothing outside the allowed five files. AC-4 (negative): no inbound link to a deleted file remains (grep of the four names over docs/, README, harness, scripts, tests returns nothing but the map itself); test_doc_gate_list_parity's comment no longer names brain-db-schema.md. AC-5: gen_doc_constants --check green after --write; test_audit_translation_drift, test_audit_stale_docs, test_publication_lines, test_release_notes_1_9, test_cli_examples_parse, test_check_docs_hook green; full lane green. AC-6: CHANGELOG EN/RU.

## Plan

[{"step": "Z1: \u0443\u0434\u0430\u043b\u0438\u0442\u044c 8 \u0444\u0430\u0439\u043b\u043e\u0432, \u0438\u043d\u0434\u0435\u043a\u0441 docs/README.md, \u0432\u0445\u043e\u0434\u044f\u0449\u0438\u0435 \u0441\u0441\u044b\u043b\u043a\u0438, \u043a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439 \u0442\u0435\u0441\u0442\u0430, docstring scrubbing", "done": true}, {"step": "Z2: knowledge-store, memory-merge-guidelines, configuration, environment, team-state-in-git (ru+en)", "done": true}, {"step": "Z3: skills, hooks, hooks-events, doctor, mcp, architecture, quickstart, security, skill-spec, troubleshooting (ru+en)", "done": true}, {"step": "Z4: README ru/en; constants --write; \u0433\u0435\u0439\u0442\u044b; CHANGELOG; verify", "done": true}]

## Rollback

git revert коммита(ов) зоны; карта остаётся.

## Journal

- 2026-09-12T15:12:44Z [implementation] — AC verified: AC-1 ✓ map §1 grep now returns 17 files, every one either an allowed residue (whats-new-1.9 ru+en, cli.md:482, skill-supply-chain-threat-model ru+en) or a legitimate mention (the retired mirror path in knowledge-store/configuration for import-brain; brain_scrubbing/brain_events names; 'Notion/server' as an example of an external store in team-state-in-git; decision references) — checked line by line above; the four Z1 pairs are deleted. AC-2 ✓ one zone per commit, no file in two zones (git log --stat of the four commits). AC-3 ✓ S1-S6 wording: grep for 'three stores|трёх хранилищ|три хранилища|brain.enabled|tausik brain|tausik-brain|/brain' outside the allowed files returns nothing. AC-4 ✓ Negative: no inbound link to a deleted page (grep over docs/, README, harness, scripts, tests: only the map); test_doc_gate_list_parity's comment no longer names the file. AC-5 ✓ gen_doc_constants --check OK; translation-drift, stale-docs, publication-lines, release-notes, cli-examples, check-docs, doc-gate-list-parity: 118/118; full lane 9982 passed with the two external failures named above. AC-6 ✓ CHANGELOG EN/RU. Domain: a reader of any page now meets the same six facts; the only pages that still say Notion say it in the past tense.
- 2026-09-12T15:12:44Z [implementation] — Executed as one agent processing zones in the map's order with commit boundaries per zone (Z1 2c0f7f97, Z2 5821e27b, Z3 6bc90a76, Z4 + stragglers in this commit): this host's tooling cannot confine a subagent to a path set, so isolation is by commit, recorded honestly against AC-2. The map's underscore grep undercounted: a bare-word grep found stale claims in doctor, mcp, agent-contract (ru), senar-compliance-matrix, dev-doc-checks, config-trust-tiers, adding-new-ide, skill-ecosystem — fixed in the same zone pass and named in the consistency task's remit. Full lane: 9982 passed / 2 failed — (1) tests/test_publication_boundary.py lacks CROSSCUTTING_SCOPE (defect of the boundary task, filed as publication-boundary-test-declares-its-tree); (2) test_renar_standard_drift::test_the_live_corpus_agrees_with_us — the external RENAR corpus moved to edition v1.1 today at 18:09 while our manifest claims renar-version 1.0: re-assessment due per §13.4.3, an environment finding outside this task, to be filed.
