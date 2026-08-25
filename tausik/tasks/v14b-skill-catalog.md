---
slug: v14b-skill-catalog
title: "B7: tausik skill catalog — discovery от подключённых repos"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/skill_repos.py, scripts/service_skills.py, scripts/project_parser_ops.py (skill subparser), scripts/project_cli_extra.py (cmd_skill dispatch), harness/{claude,cursor}/mcp/project/handlers.py + tools.py, tests/test_skill_catalog.py (new), docs/{en,ru}/cli.md, docs/{en,ru}/mcp.md, CHANGELOG.md, CHANGELOG.ru.md, README.md, README.ru.md, AGENTS.md, docs/_generated/constants.json"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T23:29:49Z"
---

## Goal

Сейчас user не знает какие skills есть в Kibertum/tausik-skills. Добавить tausik skill catalog [<repo-name>] — fetches tausik-skills.json из подключённых repos и показывает таблицу name/description/category. Простой discovery без web UI.

## Acceptance Criteria

1. service_skills.SkillsMixin.skill_catalog(vendor_dir, repo_name=None) → list[dict] {name, repo, description, category, triggers, requires}. repo_name None = все cloned repos; конкретное имя = только этот repo. 2. Unknown repo_name → ServiceError 'repo X not configured or not cloned'. 3. CLI: tausik skill catalog [<repo-name>] [--json] печатает таблицу name/category/repo/description (или JSON). 4. skill_repos.repo_list_all_skills extended: добавлено поле 'category' в каждую запись (best-effort из manifest skill entry, fallback ''). 5. MCP: tausik_skill_catalog с optional repo_name + json output (project tool count 95→96, mirror в claude+cursor handlers/tools). 6. Negative: пустой vendor_dir → возвращает [] без exception. 7. Tests: tests/test_skill_catalog.py с ≥6 cases (all repos, single repo, unknown repo, empty vendor, category fallback, JSON output). 8. docs/{en,ru}/cli.md в секции Skills добавлено `skill catalog`. 9. docs/{en,ru}/mcp.md секция Skills + `tausik_skill_catalog`. 10. CHANGELOG.md + CHANGELOG.ru.md. 11. README/AGENTS/docs MCP counts 95→96 main 102→103 + total. 12. ruff + mypy + pytest + filesize green.

## Plan

[{"step": "Extend skill_repos.repo_list_all_skills with category + add repo_catalog(repo_name=None) helper", "done": true}, {"step": "Add SkillsMixin.skill_catalog static method delegating to skill_repos", "done": true}, {"step": "CLI: subparser tausik skill catalog [name] [--json] + dispatch in project_cli_extra", "done": true}, {"step": "MCP: tausik_skill_catalog tool schema + handler (claude + cursor)", "done": true}, {"step": "Tests/test_skill_catalog.py with 6+ cases", "done": true}, {"step": "Docs: cli.md en/ru + mcp.md en/ru", "done": true}, {"step": "CHANGELOG en/ru + bump tool counts in README/AGENTS/architecture (95\u219296, 102\u2192103, 109\u2192110)", "done": true}, {"step": "ruff + mypy + pytest + filesize gates", "done": true}]

## Rollback

## Journal

- 2026-05-06T23:29:49Z [implementation] — AC verified: 1-12 ✓ repo_catalog + skill_catalog service + CLI + MCP + 10 tests + docs en/ru + CHANGELOG en+ru + tool counts 95→96/102→103/109→110 + test count 3089→3099 + ruff/mypy/pytest 2972 green
