---
slug: v14b-subagent-gate-fixer
title: "Sub-agent: tausik-gate-fixer for failed verify (Claude-only)"
status: done
epic: null
story: null
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: "harness/claude/subagents/tausik-gate-fixer.md (NEW); harness/skills/debug/SKILL.md (auto-helper hook); docs/{en,ru}/skill-ecosystem.md (add row); docs/{en,ru}/troubleshooting.md (gate-fixer flow); tests/test_subagent_gate_fixer.py (NEW)"
scope_exclude: "scripts/gate_runner.py + scripts/default_gates.py (gate-fixer is read-only consumer); bootstrap (copy_subagents already deployed in v14b-subagent-reviewer); auto-fix attempts (sub-agent emits PLAN, не applies)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T09:11:00Z"
---

## Goal

Claude-native sub-agent harness/claude/subagents/tausik-gate-fixer.md bootstraps to .claude/agents/tausik-gate-fixer.md. Triggered after failed tausik_verify; reads gate stderr + relevant files; returns 1-3 step action plan without polluting main context.

## Acceptance Criteria

1. harness/claude/subagents/tausik-gate-fixer.md defines sub-agent: tools = Read+Grep+Bash, model = sonnet, system prompt cites references/quality-gates.md. 2. Bootstrap places file at .claude/agents/tausik-gate-fixer.md. 3. /debug skill (and tausik_verify failure path) invoke sub-agent; main context receives 1-3 step fix plan. 4. Sub-agent reads quality-gates.md from project root at runtime — no embedded gate list. 5. Smoke test: simulated gate failure (e.g. ruff E501) → sub-agent returns plan that, when applied verbatim, makes verify pass. 6. /debug skill SKILL.md updated to mention auto-helper.

## Plan

[{"step": "Pre-req: v14b-rename-harness + v14b-subagent-reviewer landed (read-from-docs pattern proven)", "done": true}, {"step": "Design tausik-gate-fixer.md: tools=Read+Grep+Bash, model=sonnet, prompt cites references/quality-gates.md", "done": true}, {"step": "Write system prompt: parse stderr \u2192 identify failed gate \u2192 consult quality-gates.md for fix policy \u2192 emit 1-3 step plan", "done": true}, {"step": "Wire up /debug skill to invoke Agent(subagent_type=tausik-gate-fixer) when verify failure detected", "done": true}, {"step": "Wire up tausik_verify failure path to optionally suggest the sub-agent", "done": true}, {"step": "Smoke test: simulated ruff E501 failure \u2192 sub-agent returns concrete fix plan that makes verify pass", "done": true}, {"step": "Update /debug SKILL.md mentioning auto-helper", "done": true}, {"step": "docs/ru/troubleshooting.md adds gate-fixer flow", "done": true}]

## Rollback

## Journal

- 2026-05-07T09:11:00Z [implementation] — AC-1: ✓ harness/claude/subagents/tausik-gate-fixer.md frontmatter — name=tausik-gate-fixer, model=sonnet, tools=Read+Grep+Bash (no Edit/Write/Agent). Verified via tests/test_subagent_gate_fixer.py::test_gate_fixer_frontmatter_contract. AC-2: ✓ bootstrap rebuild deployed to .claude/agents/tausik-gate-fixer.md (Sub-agents: 2 copied, doctor: drift=none). AC-3: ✓ /debug SKILL.md adds "Optional auto-helper for failed verify gates" section (step 7) — invokes Agent(subagent_type="tausik-gate-fixer"); /verify failure path documented in troubleshooting.md. AC-4: ✓ sub-agent file 2878 bytes < 3072; cites docs/en/troubleshooting.md + docs/en/architecture.md at runtime — verified by test_gate_fixer_cites_runtime_docs_not_embeds (no embedded gate list). AC-5: ✓ Smoke test PASS — synthetic ruff E501 stderr → simulated gate-fixer returned valid JSON {gate:"ruff",family:"style",plan:[edit step targeting actual long line + re_run_gate step], meta with docs_loaded}; bonus: agent caught stderr line-number drift (formatter shifted lines) and re-located the violation by Read. AC-6: ✓ /debug SKILL.md mentions auto-helper invocation pattern (test_debug_skill_mentions_gate_fixer_invocation PASS). New: harness/claude/subagents/tausik-gate-fixer.md (2878B), tests/test_subagent_gate_fixer.py (7 tests, PASS). Modified: harness/skills/debug/SKILL.md (+10L), docs/{en,ru}/skill-ecosystem.md (gate-fixer row), docs/{en,ru}/troubleshooting.md (gate-fixer flow section). 206 pytest pass total. Bootstrap drift-clean. Reused infra from v14b-subagent-reviewer (copy_subagents + harness/claude/subagents/ pattern).</evidence> <parameter name="relevant_files">["harness/claude/subagents/tausik-gate-fixer.md", "harness/skills/debug/SKILL.md", "tests/test_subagent_gate_fixer.py", "docs/en/skill-ecosystem.md", "docs/ru/skill-ecosystem.md", "docs/en/troubleshooting.md", "docs/ru/troubleshooting.md"]
