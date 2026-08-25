---
slug: v15-doc-parity-ru
title: "Bilingual parity: 4 RU-файла + troubleshooting RU секции + agent-contract EN"
status: done
epic: v15-release-polish
story: v15-polish-public
complexity: medium
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "docs/ru/plan-review.md"
  - "docs/ru/plan-stacks.md"
  - "docs/ru/skill-patterns.md"
  - "docs/ru/skill-spec.md"
  - "docs/ru/troubleshooting.md"
  - "docs/en/agent-contract.md"
  - "site/.vitepress/config.ts"
scope_tools: []
depends_on: []
completed_at: "2026-06-13T13:43:03Z"
---

## Goal

Закрыть EN↔RU parity-гэпы: создать RU-переводы plan-review.md, plan-stacks.md, skill-patterns.md, skill-spec.md; добавить в RU troubleshooting.md 3 отсутствующие секции (prompt caching, Shared Brain, RAG); решить судьбу agent-contract (есть только RU — перевести в EN или оставить RU-only осознанно). Sidebar config.ts обновить.

## Acceptance Criteria

AC1: docs/ru/{plan-review,plan-stacks,skill-patterns,skill-spec}.md created as faithful RU translations of the EN sources (same headings/structure/links, code blocks verbatim). AC2: docs/ru/troubleshooting.md has parity with EN for the prompt-caching / Shared-Brain / RAG sections — add only genuinely missing ones (verified by header diff vs EN). AC3: agent-contract fate decided and recorded (tausik decide) — RU-only kept consciously OR translated to EN; no dangling EN link to a missing file. AC4: site/.vitepress/config.ts RU Internals sidebar lists the 4 new RU docs. AC5: pnpm build passes (no dead links from new RU files); gen_doc_constants --check green. AC6 (negative/boundary): if any new RU doc contains a relative link that does not resolve after sync, or a sidebar entry points to a missing file, pnpm build FAILS and the change is not shipped — no broken/empty RU pages.

## Plan

## Rollback

git checkout site/.vitepress/config.ts docs/ru/troubleshooting.md && rm -f docs/ru/{plan-review,plan-stacks,skill-patterns,skill-spec}.md docs/en/agent-contract.md — pure docs/sidebar; revert = drop new RU files + restore config.ts & troubleshooting.md.

## Journal

- 2026-06-13T13:42:48Z [implementation] — Done: created docs/ru/{plan-review,plan-stacks,skill-patterns,skill-spec}.md (faithful RU translations, code blocks verbatim, no relative-link changes). AC2 finding — RU troubleshooting.md ALREADY has Brain(L128)/RAG(L136)/Prompt-caching(L142) sections; header-diff vs EN confirms the 3 named sections are NOT missing → nothing added (honest no-op, avoids duplication). AC3 — agent-contract kept RU-only (decision #98); i18n-strategy.md:27 already documents it as deliberate exception, no EN dead link. AC4 — config.ts RU Internals sidebar now lists the 4 new docs (mirrors EN). Build PASS (6.96s).
- 2026-06-13T13:43:00Z [implementation] — AC verified: AC1 ✓ 4 RU files created (plan-review/plan-stacks/skill-patterns/skill-spec), faithful translations, headings+structure+code blocks preserved. AC2 ✓ troubleshooting parity verified by header-diff — Brain/RAG/Prompt-caching already present in RU; no missing sections to add. AC3 ✓ agent-contract decided RU-only (decision #98), no EN dead link (verified: only EN ref is i18n-strategy.md:27 describing it as ru-only). AC4 ✓ config.ts RU Internals sidebar lists all 4 new docs. AC5 ✓ pnpm build PASS (6.96s, new RU pages render, zero dead links) + gen_doc_constants --check OK. AC6 (negative) ✓ build fail-closed — proven green only after all new RU files + sidebar links resolve; any unresolved relative link would error the build. Security: pure docs/sidebar — no runtime/DB/auth/input surface, zero threat surface. Verify run #706 signed receipt.
