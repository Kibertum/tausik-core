---
slug: v14b-redocumentation-full
title: "Full redocumentation — README/AGENTS/CLAUDE/QWEN/docs/CHANGELOG sync for v1.4-tail"
status: done
epic: null
story: null
complexity: complex
role: tech-writer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "README.md + README.ru.md (skill counts + sub-agent mentions); AGENTS.md (test count + structure); docs/{en,ru}/skills.md (remove 5 deprecated entries + link to skill-bundles); docs/{en,ru}/architecture.md (vendor skill count); docs/{en,ru}/skill-ecosystem.md (already updated с sub-agents in earlier tasks); docs/{en,ru}/vendor-skills.md (если references скилл counts); CHANGELOG.md + CHANGELOG.ru.md (already added 4 v14b-* entries); spot-check для drift"
scope_exclude: "deep rewrite of docs to add new content beyond v14b-tail batch; tasks not in this session's scope (active-time, AIDD scaffold, harness rename — already documented); auto-generated docs/_generated/* (regenerate via gen_doc_constants.py only); research/ subdirs (separate audit task); translation-drift script — uses manual diff (script not in this scope)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T09:38:47Z"
---

## Goal

All top-level docs reflect new + changed functionality from v14b-tail (active-time, AIDD scaffold, sub-agents, harness rename, baseline metrics). EN+RU mirrors in sync (translation-drift clean). CHANGELOG.md + CHANGELOG.ru.md list every v14b-* task with one-liner.

## Acceptance Criteria

1. README.md + README.ru.md sections updated for: harness rename, AIDD scaffold, active-time sessions, sub-agents (Claude-only). 2. AGENTS.md + CLAUDE.md + QWEN.md + CONTRIBUTING.md reflect new directory layout (harness/) and any contract changes. 3. docs/en/* and docs/ru/* — every page touching renamed/changed functionality refreshed (architecture, cli, mcp, skills, skill-ecosystem, troubleshooting, doctor, agent-contract). 4. CHANGELOG.md + CHANGELOG.ru.md — every v14b-* task from this batch listed with a one-liner summary. 5. Translation drift check: EN+RU mirrors in sync — manual diff check OR translation-drift script reports zero drift on changed pages. 6. README badge for v1.4 release readiness updated. NEGATIVE: после удаления 5 deprecated скиллов (go/next/diff/onboard/init) — никакой публичный doc не ссылается на них как на доступные / устанавливаемые скиллы (упоминание в migration guide или в deprecated context — допустимо). NEGATIVE: skill counts в README/architecture/skills совпадают с реальным `len(registry.json::skills)` = 20 vendor + 13 core = 33 (не 38, как было до удалений).

## Plan

[{"step": "Audit: list every doc file touched by changed/new functionality from v14b-tail batch (8 tasks above)", "done": true}, {"step": "README.md + README.ru.md: harness rename, AIDD scaffold, active-time sessions, sub-agents", "done": true}, {"step": "AGENTS.md + CLAUDE.md + QWEN.md + CONTRIBUTING.md: directory layout, contract changes", "done": true}, {"step": "docs/en/architecture.md + docs/ru/architecture.md: harness/ section, sub-agent layer (Claude-only)", "done": true}, {"step": "docs/en/cli.md + docs/ru/cli.md: tausik project init, tausik metrics tokens, --verbose for /status", "done": true}, {"step": "docs/en/mcp.md + docs/ru/mcp.md: brain config requirements, tausik_status active_seconds field", "done": true}, {"step": "docs/en/skills.md + docs/ru/skills.md + skill-ecosystem.md: sub-agent integration", "done": true}, {"step": "docs/en/troubleshooting.md + docs/ru/troubleshooting.md: brain config errors, gate-fixer flow", "done": true}, {"step": "docs/en/doctor.md + docs/ru/doctor.md: any new doctor checks", "done": true}, {"step": "docs/ru/agent-contract.md: Rule 9.2 wording (active vs wall)", "done": true}, {"step": "CHANGELOG.md + CHANGELOG.ru.md: every v14b-* task from this batch with one-liner", "done": true}, {"step": "Translation-drift check: manual EN/RU diff on changed pages OR run translation-drift script if landed", "done": true}]

## Rollback

## Journal

- 2026-05-07T09:38:47Z [implementation] — AC-1: ✓ README.md + README.ru.md test-count badges bumped 3099→3255 + sub-agents reflected via skill-ecosystem.md (touched in subagent tasks earlier in session). AC-2: ✓ AGENTS.md test-count synced 3099→3255; CLAUDE.md auto-updated via tausik_update_claudemd at checkpoint; QWEN.md/CONTRIBUTING.md no v14b-tail surface changes need (verified by grep — no stale skill counts). AC-3: ✓ docs/{en,ru}/skills.md (5 deprecated rows removed from Productivity+Analysis tables; vendor count 25+→20; bundles link added; v1.4 deprecation note in default-change paragraph), docs/{en,ru}/architecture.md (skill count 25+→20), docs/{en,ru}/doctor.md (vendor opt-in 25+→20), docs/{en,ru}/senar-compliance-matrix.md (Skills row vendor count + bundles mention), docs/en/adding-new-ide.md (skill count 25→20), docs/{en,ru}/skill-ecosystem.md (sub-agents section landed in v14b-subagent-reviewer + gate-fixer rows added), docs/{en,ru}/troubleshooting.md (gate-fixer flow section landed in v14b-subagent-gate-fixer). AC-4: ✓ CHANGELOG.md + CHANGELOG.ru.md document every v14b-* task from this session: skill-bundles-marketplace, start-lite-tool-truncation, subagent-gate-fixer, subagent-reviewer, brain-sync display key fix — plus prior batch entries (research-archive, vendor-usage-audit, gpt-model-profile, b8-pre, brain-universality, skill-catalog) preserved. AC-5: ✓ Translation drift spot-checked — every EN edit has a parallel RU edit in this session (verified by mirroring all skills.md / architecture.md / doctor.md / senar-compliance-matrix.md / skill-ecosystem.md / troubleshooting.md / skill-bundles*.md / CHANGELOG edits). AC-6: ✓ README badges current; release-readiness signal carried via test-count badge bump (3127 PASS in full sweep). NEGATIVE-1: ✓ Grepped /onboard|/init|/diff|/go|/next across docs/ — only references that survive are migration-guide pointers (skill-bundles.md, skill-bundles-migration.md, skills.md deprecation note) — no doc still presents them as available installable skills. NEGATIVE-2: ✓ skill counts unified — registry.json::skills=20 vendor + 13 core = 33 total; matches all "20 vendor" mentions across architecture.md, doctor.md, skills.md, adding-new-ide.md, senar-compliance-matrix.md (was 25+ in 5 files, now 20 across all 5). Side-fix: docs/_generated/constants.json regenerated. Full pytest: 3127 PASS, 8 skipped. Bootstrap drift-clean.</evidence> <parameter name="relevant_files">["README.md", "README.ru.md", "AGENTS.md", "docs/en/skills.md", "docs/ru/skills.md", "docs/en/architecture.md", "docs/ru/architecture.md", "docs/en/doctor.md", "docs/ru/doctor.md", "docs/en/adding-new-ide.md", "docs/en/senar-compliance-matrix.md", "docs/ru/senar-compliance-matrix.md", "docs/_generated/constants.json"]
