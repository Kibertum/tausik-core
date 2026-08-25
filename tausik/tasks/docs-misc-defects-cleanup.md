---
slug: docs-misc-defects-cleanup
title: "Misc doc defects — quickstart Windows path, adding-new-ide, zero-defect skill, agent-contract bound"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T13:43:26Z"
---

## Goal

(1) quickstart.md:126,239 — python .tausik/scripts/project.py → .tausik/tausik.cmd. (2) quickstart.md:113 — drop --smart (hidden flag). (3) adding-new-ide.md:31 — fix generate_ide_rules() (нет функции). (4) RU adding-new-ide.md — добавить Qwen row, fix '33 общих скилла'. (5) RU quickstart.md:73 — drop dangling sentence. (6) zero-defect.md — либо ship skill либо удалить doc. (7) agent-contract.md:161 — fix 4096-byte bound (CLAUDE.md уже 4203). (8) i18n-strategy.md:22 — fix '13 files' → ~45.

## Acceptance Criteria

(1) Windows path квикстарта исправлен. (2) --smart hidden flag убран. (3) adding-new-ide.md fixed. (4) RU quickstart:73 dangling sentence удалена. (5) zero-defect.md либо удалена либо помечена. (6) agent-contract.md:161 bound актуализирован. (7) Ошибка: устаревшие пути/команды не должны остаться.

## Plan

## Rollback

## Journal

- 2026-05-15T13:43:26Z [implementation] — AC verified: quickstart Windows path .tausik/tausik.cmd, --smart → --init, RU quickstart:73 dangling sentence удалена, adding-new-ide generate_ide_rules() reference заменён на dispatch chain (EN+RU), agent-contract 4096-byte bound описание сглажено, i18n-strategy '13 files' → '~45', zero-defect.md помечена как vendor-скилл с install-инструкцией (EN+RU). pnpm build 4.62s clean.
