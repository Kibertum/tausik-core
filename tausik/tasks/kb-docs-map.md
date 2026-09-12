---
slug: kb-docs-map
title: "Карта затронутой документации и разбиение на зоны для роя"
status: done
epic: release-19-renar-conformance
story: knowledge-sheds-notion-and-its-hygiene
complexity: medium
role: architect
stack: null
tier: light
call_budget: 20
defect_of: null
scope: "Карта-документ в docs/ru/research + журнал; ни одной правки самих затронутых документов."
scope_exclude: "Не переписывать документацию (это kb-docs-swarm), не трогать код, не релизить."
relevant_files:
  - "docs/ru/research/notion-departure-doc-map.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "docs/ru/research/notion-departure-doc-map.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/kb-docs-map.md"
  - "tausik/stories/knowledge-sheds-notion-and-its-hygiene.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T15:00:12Z"
---

## Goal

ПОДГОТОВКА К РОЮ, без неё рой бесполезен. Составить карту всех мест в docs/ru и docs/en, затронутых переходом: shared-brain (281 строка, переписывается почти целиком), architecture, cli, mcp, agent-contract, quickstart, configuration, README на двух языках. Разбить на НЕПЕРЕСЕКАЮЩИЕСЯ зоны — по одному владельцу на файл, иначе параллельные агенты будут править один файл и затирать друг друга. Отдельно выписать сквозные утверждения, которые встречаются в нескольких документах и должны измениться согласованно: где живут знания, нужен ли Notion, как настраивается общая база, что можно и нельзя выгрузить в git. Учесть doc-drift гейты и счётчики в constants.json — они тоже часть карты.

## Acceptance Criteria

AC-1: карта в docs/ru/research/notion-departure-doc-map.md покрывает КАЖДЫЙ файл docs/{ru,en}, README ru+en и docs/README.md, где grep -i 'notion|shared brain|tausik-brain|brain_' даёт хоть одно совпадение вне research/ и вне whats-new-1.8 (история 1.8 не переписывается) — число файлов названо и сосчитано командой в самой карте. AC-2: файлы разбиты на непересекающиеся зоны с одним владельцем на файл; ru- и en-зеркало одного файла в одной зоне; каждая зона получает судьбу файла: удалить целиком / переписать раздел / поправить строку. AC-3: сквозные утверждения (где живут знания; нужен ли Notion; как настраивается общее хранилище; что может покинуть машину и git; счётчики) выписаны с их каноническими формулировками и списком файлов, где каждое встречается. AC-4: перечислены гейты, которые рой обязан пройти: constants.json (hooks 22, skills 13, MCP 146), test_audit_translation_drift (парность ru/en), test_publication_lines, test_release_notes_1_9, test_cli_examples_parse, test_doc_gate_list_parity (упоминает brain-db-schema.md), test_check_docs_hook, docs/README.md индекс, кросс-ссылки на удаляемые файлы. AC-5 (negative): для удаляемых файлов перечислены все входящие ссылки, чтобы после удаления не осталось битых — проверено grep в карте. AC-6: CHANGELOG EN/RU запись.

## Plan

[{"step": "\u0418\u043d\u0432\u0435\u043d\u0442\u0430\u0440\u044c grep \u043f\u043e docs/, README, docs/README.md; \u0438\u0441\u043a\u043b\u044e\u0447\u0438\u0442\u044c research/ \u0438 whats-new-1.8", "done": true}, {"step": "\u0417\u043e\u043d\u044b \u0438 \u0441\u0443\u0434\u044c\u0431\u044b \u0444\u0430\u0439\u043b\u043e\u0432; \u0432\u0445\u043e\u0434\u044f\u0449\u0438\u0435 \u0441\u0441\u044b\u043b\u043a\u0438 \u043d\u0430 \u0443\u0434\u0430\u043b\u044f\u0435\u043c\u044b\u0435", "done": true}, {"step": "\u0421\u043a\u0432\u043e\u0437\u043d\u044b\u0435 \u0443\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u044f \u0438 \u0433\u0435\u0439\u0442\u044b; CHANGELOG; verify", "done": true}]

## Rollback

карта это артефакт планирования; откат не требуется

## Journal

- 2026-09-12T15:00:01Z [implementation] — AC verified: AC-1 ✓ docs/ru/research/notion-departure-doc-map.md §1 quotes the grep and its count (45 files; whats-new-1.8 and research/ excluded with reasons). AC-2 ✓ §2: Z1 retire (8), Z2 stores (10), Z3 surface (22), Z4 root (5) = 45, ru/en pairs never split; each file has a fate and the exact lines. AC-3 ✓ §3: six cross-cutting claims S1-S6 with canonical wording and the pages carrying each. AC-4 ✓ §4: nine gates with how not to fail them (constants, translation drift, publication lines, release notes, cli examples, doc-gate-list parity comment, stale docs, index, cross-links). AC-5 ✓ Negative: §2 Z1 lists every inbound link to the four retiring docs (grep over docs/, README, harness, scripts, tests) including the non-docs one in brain_scrubbing.py:18 and the parity test comment. AC-6 ✓ CHANGELOG EN/RU. Facts checked against the tree before writing: hooks-events.md has no en mirror (stale-docs audit tolerates it), research/ is excluded from the mirror audit, test_doc_gate_list_parity.py:77 names brain-db-schema.md. Domain: the swarm can start from Z1 with zero ambiguity about who owns which pair.
