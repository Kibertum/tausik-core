---
slug: nothing-scans-the-installed-harness-state
title: "Никто не сканирует установленную обвязку: мы проверяем входящее и не смотрим на то, что уже лежит"
status: done
epic: release-1-11-3
story: release1113-quality-ratchets
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/harness_audit.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_doctor.py"
  - "tests/test_harness_audit.py"
  - "docs/en/doctor.md"
  - "docs/ru/doctor.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/service_doctor*.py"
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T19:03:20Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#98"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Установленное состояние обвязки — .claude, MCP-конфиг, память — регулярно проверяется на то, что в него могло приехать: невидимый Unicode, императивы в записях памяти, дрейф хуков от исходников.

## Acceptance Criteria

1. `tausik doctor --harness-audit` — детерминированный скан установленного состояния: развёрнутые профили IDE, MCP-конфиги, записи памяти. Без LLM и без сети.
2. Проверки переиспользуют существующее: install-guard невидимого Unicode, детектор секретов, сравнение с исходниками в harness/. Второй набор паттернов НЕ пишется.
3. Названа асимметрия, которую задача закрывает: подписи и install-guard защищают ВХОДЯЩЕЕ, но после установки состояние никто не перечитывает, а инъекция приезжает именно в него.
4. Записи памяти проверяются на императивные конструкции, адресованные будущему агенту, — память есть неревьюенный контекст, и это надо назвать вслух, а не считать очевидным.
5. Вердикт — WARN, не BLOCK: ложные срабатывания на легитимных императивных записях неизбежны, а гейт, блокирующий работу на своей же памяти, будет отключён целиком.
6. НЕГАТИВНЫЙ сценарий: скан проверен на ПОДСАЖЕННОМ образце — невидимый Unicode в SKILL.md, императив в записи памяти, изменённый развёрнутый хук. Не находит хотя бы один — детектор сломан.
7. НЕГАТИВНЫЙ сценарий: точность на живом проекте. Больше пяти ложных тревог на чистом дереве — порог поднимается или проверка снимается.

## Plan

## Rollback

git revert коммита; подкоманда doctor снимается

## Journal

- 2026-10-07T19:03:00Z [implementation] — AC-1: ✓ doctor --harness-audit — детерминированный скан установленного состояния (профили IDE, MCP-конфиги, память), без LLM/сети; живой прогон: 0 findings, exit 0. AC-2: ✓ переиспользовано, вторых наборов нет: skill_content_scan (Unicode + суффикс-лист), hooks/secret_scan._PATTERNS (importlib, tests/test_harness_audit.py::test_secret_patterns_come_from_the_hook_module), scripts_drift_names + _harness_drift_names (дрейф). AC-3: ✓ асимметрия названа: docstring модуля, первый экран аудита, docs/en+ru/doctor.md. AC-4: ✓ память сканируется на императивы будущему агенту: tests/...::test_planted_memory_directive_is_found; в выводе — «unreviewed context». AC-5: ✓ вердикт WARN, не BLOCK: tests/...::test_audit_command_exits_clean_even_with_findings (return None, exit 0). AC-6: ✓ подсаженный образец находится ВЕСЬ: tests/...::test_a_planted_sample_is_found (3 параметра: Unicode U+E0001 в SKILL.md, AWS-ключ в settings.json, изменённый zz_probe_hook.py) + память. AC-7: ✓ точность на живом дереве: tests/...::test_live_tree_stays_under_the_false_alarm_threshold (≤5; первый прогон поймал 9/10 шума из node_modules/worktrees — исключения измерены и записаны). Domain: живой `.tausik/tausik doctor --harness-audit` на этом проекте печатает асимметрию и «no findings» — скан реально читает .claude/.cursor/.kilo/.mcp.json и память этой машины. Verify: run #3634 PASS (8/0/1; scoped 36/670 files, 930 passed, 16 skipped), handle 3634.3c613c41360481cc84babcac01d35ae3. Dedupe удержан 282/669 (parametrized merge подсаженных кейсов; два однострочных теста влезли в существующие группы — переформлены).
- 2026-10-07T19:03:14Z [implementation] — NO-DEAD-END: the 1 red run (#3633) was the first verify of this task finding my own drafting noise - unused noqa comments (RUF100) and three planted tests sharing one AST shape (dedupe growth 283/672). Both are landing defects of this diff, not failed approaches: noqa comments deleted, planted trio merged into one parametrized test (the dedupe gate's own prescribed remedy). Next run green (#3634).
