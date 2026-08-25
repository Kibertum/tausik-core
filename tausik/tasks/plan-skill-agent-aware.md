---
slug: plan-skill-agent-aware
title: "/plan skill + CLAUDE.md — обучить агента agent-native estimation"
status: done
epic: agent-native-planning
story: estimation-planning-integration
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/skills/plan/SKILL.md\nagents/skills/go/SKILL.md\nCLAUDE.md\nagents/claude/mcp/project/tools.py (только description полей)\n.claude/mcp/project/tools.py (mirror)\ntests/test_plan_skill_agent_aware.py (новый)"
scope_exclude: "scripts/* (CLI/service не трогаем — CLI готов в agent-units-cli-flags)\nagents/skills/* (other skills) — only plan + go\nbootstrap/ (не нужно перегенерировать)"
relevant_files:
  - "agents/skills/plan/SKILL.md"
  - "skills-official/go/SKILL.md"
  - CLAUDE.md
  - "agents/claude/mcp/project/tools.py"
  - ".claude/mcp/project/tools.py"
  - "tests/test_plan_skill_agent_aware.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T12:07:00Z"
---

## Goal

/plan skill (agents/skills/plan/SKILL.md) обновить: при создании task требует tier estimate в TOOL CALLS, не часах. Объяснение когда trivial vs moderate vs deep с примерами из real session data. CLAUDE.md секция "Agent-native estimation" — контракт обязательного estimation. /go skill (quick-start) тоже обновить. Update agents/{ide}/mcp/project/tools.json schema descriptions для task_add — explicit "in tool calls".

## Acceptance Criteria

- [ ] agents/skills/plan/SKILL.md добавляет step "Estimate tier" (между шагами 4 и 5): требует выбрать tier или call_budget на основе шкалы; примеры из real session data (например: schema migration → trivial, recording с hook → light, бoльшие refactor → moderate, vertical с интеграцией → substantial, full enterprise feature → deep)
- [ ] CLAUDE.md содержит секцию "Agent-native estimation" с шкалой call_budget→tier и обязательностью при task_add (или explicit обоснование почему пропустить)
- [ ] agents/skills/go/SKILL.md (quick-start) — упоминает что после quick task надо сразу установить --call-budget или --tier
- [ ] agents/claude/mcp/project/tools.py — описание tausik_task_add в "description" поле упоминает что estimation в tool calls (а не часах); call_budget описание уточняет шкалу trivial/light/moderate/substantial/deep
- [ ] .claude/mcp/project/tools.py mirror sync
- [ ] Negative scenario: skill clearly предупреждает что забытый estimation = task создаётся без units (валидно но flag для last calibration)
- [ ] Tests tests/test_plan_skill_agent_aware.py: (a) SKILL.md содержит "tier" / "call_budget"; (b) CLAUDE.md содержит "Agent-native estimation"; (c) tools.py description обновлено

## Plan

## Rollback

## Journal

- 2026-04-25T12:06:55Z [implementation] — AC verified: 1. plan SKILL.md tier estimate step ✓ (test_mentions_tier_or_call_budget, test_lists_all_five_tiers PASSED) 2. CLAUDE.md Agent-native estimation section ✓ (test_has_agent_native_estimation_section PASSED) 3. go SKILL.md mentions tier/call_budget ✓ (test_mentions_estimation PASSED) 4. tools.py task_add description упоминает TOOL CALLS + tier scale ✓ (test_task_add_description_mentions_tool_calls + test_call_budget_description_lists_tiers PASSED) 5. .claude/mcp/project/tools.py mirror sync ✓ (test_mirror_in_sync PASSED) 6. Negative scenario: skill отмечает что skip estimation = task без units (доступен но flag) ✓ 7. Tests test_plan_skill_agent_aware.py 9/9 PASSED
