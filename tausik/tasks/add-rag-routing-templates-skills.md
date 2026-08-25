---
slug: add-rag-routing-templates-skills
title: "Surface search_code in templates + fix skill grep pointers"
status: done
epic: v131-blind-review-fixes
story: rag-discoverability
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_templates.py"
  - "agents/skills/zero-defect/SKILL.md"
  - "agents/skills/debug/SKILL.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-27T12:14:26Z"
---

## Goal

Bootstrap templates (CLAUDE.md/AGENTS.md/.cursorrules/QWEN.md), skills/zero-defect, skills/debug must guide agent to search_code first, Grep as fallback. Add tool-routing rubric. Closes HIGH (UX).

## Acceptance Criteria

1. bootstrap_templates.py adds TOOL_ROUTING block: code search → search_code first, Grep fallback; project knowledge → memory_search; cross-project → brain_search; 2. agents/skills/zero-defect/SKILL.md replaces 'grep the codebase' with 'search_code (RAG), Grep as fallback'; 3. agents/skills/debug/SKILL.md fixes same pattern; 4. Re-bootstrap sample to verify text appears in CLAUDE.md/AGENTS.md; 5. Negative: docs no longer say 'use grep' as primary code-discovery tool.

## Plan

## Rollback

## Journal

- 2026-04-27T12:14:26Z [implementation] — AC: 1.✓ TOOL_ROUTING block добавлен в bootstrap_templates.py с таблицей "Need / Primary / Fallback" и явной директивой "Don't reach for Grep/Glob first"; 2.✓ zero-defect/SKILL.md правило 3 заменило "grep the codebase" на "mcp__codebase-rag__search_code (RAG); fall back to Grep only if RAG is empty or stale"; 3.✓ debug/SKILL.md заменил "grep for the function" аналогично; 4.✓ build_full_body() инжектит TOOL_ROUTING между WORKFLOW и MEMORY, пайплайн bootstrap проверен (`python -c ... build_full_body` подтверждает наличие); 5.✓ Negative — теперь в нет директивы "use grep" как primary code-discovery tool ни в одном из 4 IDE templates (CLAUDE.md/AGENTS.md/.cursorrules/QWEN.md из bootstrap_templates.py).
