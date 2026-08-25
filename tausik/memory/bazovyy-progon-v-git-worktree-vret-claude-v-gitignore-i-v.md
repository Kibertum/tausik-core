---
slug: bazovyy-progon-v-git-worktree-vret-claude-v-gitignore-i-v
title: "Базовый прогон в git worktree врёт: .claude/ в .gitignore и в worktree его нет"
type: gotcha
tags:
  - baseline
  - gitignore
  - mirrors
  - testing
  - worktree
task: review-skill-supplychain-findings
edges: []
---

'git worktree add' переносит только отслеживаемые файлы. Зеркала .claude/ .cursor/ .kilo/ .qwen/ перечислены в .gitignore (.gitignore:27), поэтому в свежем worktree их нет. Тесты, которые читают реальный репозиторий (test_review_high_fixes, test_check_docs_hook, test_audit_*, test_med_findings_fix::test_mcp_mirrors_in_sync, test_plan_skill_agent_aware::test_mirror_in_sync, test_bootstrap_extension_skills), падают с FileNotFoundError на '.claude/settings.json' — это падение окружения, а не кода. В моём прогоне так получилось 11 ложных падений.

Как снимать базовое состояние: либо гонять в настоящем чекауте, либо сначала выполнить bootstrap в worktree, чтобы зеркала появились. Иначе легко выдать отсутствие .claude/ за регрессию.

Побочно: скрипт с зеркалами не коммитится — 'git show --stat' по правке скиллов покажет только scripts/skill_manager.py, хотя рабочее дерево содержит четыре синхронные копии. Отслеживаются ровно scripts/skill_manager.py и tests/test_skill_manager.py.
