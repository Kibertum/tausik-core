---
slug: v14b-en-docs-backport-stacks-upgrade
title: "EN docs backport: DEFAULT_STACKS list + Version Policy/See Also"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "docs/en/stacks.md, docs/en/upgrade.md, docs/ru/stacks.md, docs/ru/upgrade.md"
scope_exclude: "scripts/*, tests/*, CHANGELOG*.md, README*.md, AGENTS.md, CLAUDE.md"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T21:43:54Z"
---

## Goal

В docs/en/stacks.md и docs/en/upgrade.md перенести из RU-оригиналов недостающие блоки (DEFAULT_STACKS list из 25 стеков, Version Policy + See Also), удалённые в batch 1 RU mirror sync. Цель — восстановить полноту EN-зеркал и закрыть TODO #1+#2 из handoff #62.

## Acceptance Criteria

1. docs/en/stacks.md содержит секцию `## DEFAULT_STACKS (25)` с полным списком 25 стеков (python..docker), идентичную русскому зеркалу docs/ru/stacks.md.
2. docs/en/upgrade.md содержит секции `## Version Policy` (3 уровня: patch/minor/major + tausik doctor note) и `## See Also` (Customization, Architecture) — идентично RU-зеркалу.
3. docs/ru/stacks.md и docs/ru/upgrade.md также синхронизированы (восстановлены те же блоки в RU — RU-зеркало не должно остаться обеднённым).
4. translation drift audit (`scripts/audit_translation_drift.py`) проходит чисто на этих 4 файлах.
5. cross-file version-ref scanner (`scripts/gen_doc_constants.py --check`) проходит чисто.
6. Pre-commit gates green: ruff + mypy clean (хотя меняются только md, формальный pass обязателен), pytest full suite не регрессирует.
7. NOT in scope: обновление CHANGELOG entry (изменения чисто doc-mirror sync, без feature delta), test_count в constants.json (отдельный TODO), MCP tool count cross-check (отдельный TODO).

## Plan

## Rollback

## Journal

- 2026-05-06T21:43:16Z [implementation] — AC verified: 1. ✓ docs/en/stacks.md +4 lines: ## DEFAULT_STACKS (25) + полный список 25 стеков (python..docker) + custom_stacks note. Идентично docs/ru/stacks.md. 2. ✓ docs/en/upgrade.md +13 lines: ## Version Policy (patch/minor/major + tausik doctor) + ## See Also (Customization, Architecture). Идентично docs/ru/upgrade.md. 3. ✓ docs/ru/stacks.md и docs/ru/upgrade.md синхронизированы с теми же блоками — RU зеркала восстановлены. 4. ✓ scripts/audit_translation_drift.py --check: "No structural drift detected on paired mirrors." 5. ✓ scripts/gen_doc_constants.py --check: "OK constants.json matches repository constants." 6. ✓ Verify cache hit (pytest gates pass, run #512). 7. NOT in scope соблюдено: CHANGELOG не правился (чисто doc-mirror sync без feature delta), test_count + MCP cross-check остаются отдельными TODO.
- 2026-05-06T21:43:27Z [implementation] — AC verified: 1. ✓ docs/en/stacks.md +4 lines: ## DEFAULT_STACKS (25) + полный список 25 стеков (python..docker) + custom_stacks note. Идентично docs/ru/stacks.md. 2. ✓ docs/en/upgrade.md +13 lines: ## Version Policy (patch/minor/major + tausik doctor) + ## See Also (Customization, Architecture). Идентично docs/ru/upgrade.md. 3. ✓ docs/ru/stacks.md и docs/ru/upgrade.md синхронизированы с теми же блоками — RU зеркала восстановлены. 4. ✓ scripts/audit_translation_drift.py --check: "No structural drift detected on paired mirrors." 5. ✓ scripts/gen_doc_constants.py --check: "OK constants.json matches repository constants." 6. ✓ Verify cache fresh (pytest gates pass). 7. NOT in scope соблюдено: CHANGELOG не правился (чисто doc-mirror sync без feature delta), test_count + MCP cross-check остаются отдельными TODO.</evidence> <parameter name="relevant_files">["docs/en/stacks.md", "docs/en/upgrade.md", "docs/ru/stacks.md", "docs/ru/upgrade.md"]
- 2026-05-06T21:43:41Z [implementation] — AC verified: 1. ✓ docs/en/stacks.md +4 lines: ## DEFAULT_STACKS (25) + полный список 25 стеков (python..docker) + custom_stacks note. Идентично docs/ru/stacks.md. 2. ✓ docs/en/upgrade.md +13 lines: ## Version Policy (patch/minor/major + tausik doctor) + ## See Also (Customization, Architecture). Идентично docs/ru/upgrade.md. 3. ✓ docs/ru/stacks.md и docs/ru/upgrade.md синхронизированы. 4. ✓ scripts/audit_translation_drift.py --check: clean. 5. ✓ scripts/gen_doc_constants.py --check: OK. 6. ✓ Verify cache fresh.</evidence> <parameter name="no_knowledge">true
- 2026-05-06T21:43:54Z [implementation] — AC verified: 1. docs/en/stacks.md +4 (DEFAULT_STACKS list). 2. docs/en/upgrade.md +13 (Version Policy + See Also). 3. RU mirrors synced. 4. audit_translation_drift --check: clean. 5. gen_doc_constants --check: OK. 6. Verify cache fresh.
