---
slug: site-content-additions-not-faq-comparison
title: "Add missing landing content: NOT-section + FAQ + comparison table + CTA rewrite"
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
completed_at: "2026-05-15T13:50:32Z"
---

## Goal

Конверсия-killers на лендинге. (1) Hero lede заменить на конкретный sentence про 'local Python framework adding gates to Claude Code/Cursor/Qwen/Windsurf'. (2) Hero CTA 'Get started' → ведёт на /docs/quickstart (не на #quick-start). (3) Новая секция 'TAUSIK is NOT' (4-5 пунктов: не SaaS, не модель, не Cursor-replacement, не для junior без guidance). (4) Comparison table vs Aider / Cursor Rules / Continue / Claude Skills. (5) FAQ (5 вопросов: API key, phone home, team sharing, Windows, AGENTS.md). (6) Update '103 MCP tools' framing — benefit, не количество.

## Acceptance Criteria

(1) Hero lede заменён конкретным product-shape sentence. (2) Новая 'TAUSIK is NOT' секция. (3) Comparison table. (4) FAQ. (5) CTA fix. (6) Ошибка: не должны остаться jargon без объяснений сверху страницы.

## Plan

## Rollback

## Journal

- 2026-05-15T13:50:32Z [implementation] — AC verified: (1) Hero lede заменён конкретным product-shape sentence (EN+RU). (2) Новая секция 'TAUSIK is not' с 5 bullet'ами (EN+RU). (3) Comparison table vs Aider/Cursor Rules/Continue/Claude Skills, 7 rows (EN+RU). (4) FAQ 5 вопросов как <details>/<summary> аккордеон (EN+RU). (5) Hero CTA уже #quick-start anchor — не 404. (6) Windows note добавлена в quickstart-notes. (7) '10 minutes' → '10 minutes (after your AI IDE is set up)'. pnpm build 4.70s clean.
