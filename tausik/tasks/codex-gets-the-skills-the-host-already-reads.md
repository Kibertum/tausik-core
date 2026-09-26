---
slug: codex-gets-the-skills-the-host-already-reads
title: "Навыки доставляются в .codex/skills — хост их читает, а каталога нет вовсе"
status: done
epic: release-19-renar-conformance
story: codex-first-class-19
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: "bootstrap/bootstrap_copy.py (delivery already proven; do not duplicate generator work)"
relevant_files:
  - "harness/skills/start/variants/ide/codex.md"
  - "tests/test_bootstrap_skills_coverage.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "harness/skills/start/variants/ide/codex.md"
  - "tests/test_bootstrap_skills_coverage.py"
  - ".codex/skills/*"
  - ".claude/skills/*"
  - ".codex/agents/*"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-10T06:52:23Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР, смена #241. Codex читает .codex/skills и SKILL.md - обе строки присутствуют в бинаре codex.exe, как и .codex/agents. В проекте уже лежит .codex/agents с четырьмя файлами .toml, но каталога .codex/skills нет вовсе: навыки под Codex не доставляются, потому что codex отсутствует в SCAFFOLD_IDES и генератора для него нет.

ЧТО ДЕЛАЕТСЯ. Раскладка активных навыков в .codex/skills/ тем же путём, каким они кладутся остальным хостам, и с тем же профилем (IDE-оверлей codex у skill_profile уже существует - см. VALID_IDES в skill_profile_detect). Каталог .codex/ в .gitignore, то есть это развёрнутый профиль наравне с .claude/ и воссоздаётся bootstrap-ом.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Навык - это то, чем агент узнаёт процедуру проекта: /start, /task, /verify. Хост без навыков получает только AGENTS.md, то есть правила без процедур, и первое же действие делает по-своему.

## Acceptance Criteria

AC-1 После bootstrap --ide codex каталог .codex/skills/ содержит те же активные навыки, что получает claude-профиль: сравнение по ИМЕНАМ, а не по числу. AC-2 Каждый доставленный навык несёт SKILL.md - файл, по которому хост его и находит. AC-3 IDE-оверлей codex применён: тест берёт навык, у которого есть variants/ide/codex.md, и проверяет, что доставленная копия несёт содержимое оверлея, а не общий текст. AC-4 НЕГАТИВ: повторный прогон не плодит копий и не оставляет навыков, снятых с активных - удалённый из набора навык исчезает из .codex/skills/. AC-5 Существующие .codex/agents не затираются генератором навыков.

## Plan

[{"step": "\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c \u0438\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u043d\u0430\u0431\u043e\u0440 active skills \u0438 \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u0435 \u0434\u043e\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u043c\u043e\u0433\u043e Codex overlay.", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043c\u0438\u043d\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 Codex-specific delta \u043a \u0440\u0430\u0431\u043e\u0447\u0435\u043c\u0443 \u043d\u0430\u0432\u044b\u043a\u0443 /start, \u043d\u0435 \u0434\u0443\u0431\u043b\u0438\u0440\u0443\u044e\u0449\u0438\u0439 \u0431\u0430\u0437\u043e\u0432\u0443\u044e \u043f\u0440\u043e\u0446\u0435\u0434\u0443\u0440\u0443.", "done": true}, {"step": "\u0420\u0430\u0441\u0448\u0438\u0440\u0438\u0442\u044c bootstrap integration test: Claude/Codex \u043f\u043e\u043b\u0443\u0447\u0430\u044e\u0442 \u0440\u0430\u0432\u043d\u044b\u0439 \u043d\u0430\u0431\u043e\u0440 SKILL.md, Codex \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442 overlay, \u043f\u043e\u0432\u0442\u043e\u0440\u043d\u044b\u0439 \u0437\u0430\u043f\u0443\u0441\u043a \u043e\u0447\u0438\u0449\u0430\u0435\u0442 \u0441\u043d\u044f\u0442\u044b\u0439 \u043d\u0430\u0432\u044b\u043a \u0438 \u043d\u0435 \u0442\u0440\u043e\u0433\u0430\u0435\u0442 agents.", "done": true}, {"step": "\u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c bootstrap --ide all, scoped tests, dedupe audit \u0438 verify; \u0437\u0430\u0444\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u0442\u044c evidence.", "done": true}]

## Rollback

Раскладка навыков в .codex/skills; откат - git revert. Каталог в .gitignore и воссоздаётся bootstrap-ом, поэтому откат ничего не разрушает.

## Journal

- 2026-09-09T16:19:54Z [planning] — ЗАМЕР ПОСЛЕ СМЕНЫ #241 СОКРАЩАЕТ ЗАДАЧУ: bootstrap --ide codex уже раскладывает навыки — в .codex/skills/ их 14, каждый несёт SKILL.md. Делает это ОБЩИЙ шаг копирования профиля, а не отдельный генератор, поэтому строить нечего. Осталось ровно то, что не проверено: применяется ли IDE-оверлей variants/ide/codex.md, и закрепление тестом (AC-1..AC-5 остаются в силе как проверка, а не как постройка).
- 2026-09-10T06:43:20Z [implementation] — Measured active overlay gap: the only variants/ide/codex.md is under excluded _profile-demo, so no deployable skill proves Codex overlay delivery. Plan adds a minimal /start overlay plus bootstrap integration coverage; copy_skills itself already deploys Codex skills.
- 2026-09-10T06:49:16Z [implementation] — Added the deployable /start Codex overlay and integration coverage. Explicit slow test passed: 1 passed in 77.57s. bootstrap --ide all completed and deployed 14 skills to Codex plus four sub-agents.
- 2026-09-10T06:51:32Z [implementation] — AC evidence prepared: AC-1/2 Claude and Codex skill-name sets + every SKILL.md are asserted by test_codex_skills_match_claude_apply_overlay_and_preserve_agents; AC-3 explicitly rebuilds Codex and asserts its /start overlay; AC-4 creates stale skill then asserts rerun removes it; AC-5 creates user-agent.toml then asserts rerun preserves it. Evidence: python -m pytest tests/test_bootstrap_skills_coverage.py -m slow -k codex -q => 1 passed in 77.57s; python bootstrap/bootstrap.py --ide all => Codex 14 skills, 4 subagents; python -m pytest tests/test_skill_profile.py -q => 22 passed; Ruff and audit_pytest_dedupe passed.
- 2026-09-10T06:52:20Z [implementation] — AC verified: 1. ✓ Explicit slow integration test compares Claude/Codex active skill names after bootstrap. 2. ✓ The same test requires SKILL.md in every delivered Codex skill. 3. ✓ It rebuilds the Codex profile and requires the deployed /start MCP-first overlay text. 4. ✓ It creates stale skill then requires repeated bootstrap to remove it. 5. ✓ It creates user-agent.toml then requires repeated bootstrap to preserve it. Evidence: python -m pytest tests/test_bootstrap_skills_coverage.py -m slow -k codex -q => 1 passed in 77.57s; bootstrap --ide all => Codex 14 skills and 4 subagents; test_skill_profile => 22 passed; signed verify #2384 passed ruff + scoped pytest. The receipt's git-mismatch warning solely identifies prior adjacent-task work outside this task's relevant files, not an unverified current change.
