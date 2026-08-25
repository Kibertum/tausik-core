---
slug: s126-review-fixes
title: "Ревью-фиксы волны s126: prefix-match -Command, ./~ ложный home-wipe, гонка append/drain стока"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/bash_cmd_norm.py (#1), scripts/hooks/rm_wipe_detect.py (#2), scripts/hooks/hook_supervision.py (#3), tests/test_hooks.py + tests/test_bypass_telemetry.py"
scope_exclude: null
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - README.md
  - README.ru.md
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "docs/_generated/constants.json"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - "harness/claude/mcp/project/handlers.py"
  - "scripts/gate_runner.py"
  - "scripts/hooks/bash_cmd_norm.py"
  - "scripts/hooks/bash_cmd_scan.py"
  - "scripts/hooks/hook_supervision.py"
  - "scripts/hooks/rm_wipe_detect.py"
  - "scripts/hooks/secret_scan.py"
  - "scripts/service_task_done.py"
  - "tests/test_bypass_telemetry.py"
  - "tests/test_gates.py"
  - "tests/test_hooks.py"
  - "tests/test_mcp_verify_handler.py"
  - "tests/test_secret_scan_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T16:57:38Z"
---

## Goal

Адверсариальное ревью волны s126 (агент на другой модели) нашло 1 HIGH + 2 MEDIUM. (HIGH) _interpreter_payloads матчит `-c` через low.startswith('-c'), поэтому реальные powershell-флаги `-ConfigurationName`/`-CustomPipeName` перехватывают извлечение — их ЗНАЧЕНИЕ уходит как payload, а настоящий -Command не смотрится (сейчас замаскировано raw-join, живого байпаса нет, но контракт сломан). (MED) normalise_operand: `./~`, `dir/../~` схлопываются в `~` и блокируются как home-wipe, хотя реальный шелл раскрывает в $HOME только ВЕДУЩИЙ тильда — ложный блок удаления файла с именем ~ (отменяет побочную оценку в decision #177). (MED) гонка _append_pending(open+write) vs _drain_pending(os.replace): запись может лечь в уже отвязанный inode и потеряться — противоречит инварианту «промах не теряется».

## Acceptance Criteria

1. (HIGH) _interpreter_payloads матчит -Command только как непустой префикс литерала 'command' (`'command'.startswith(low[1:])`), НЕ по startswith('-c'); `-ConfigurationName Foo -Command 'X'` извлекает 'X', не 'Foo'. Регресс-тест на decoy-флаг перед -Command. 2. (MED) is_wipe_root/normalise_operand: результат `~` считается home-wipe ТОЛЬКО при ведущей тильде в исходном операнде; `rm -rf ./~` и `dir/../~` НЕ блокируются; `rm -rf ~`,`~/`,`~/*` по-прежнему блокируются. Пин-тест на ./~ allowed. 3. (MED) сток supervision: устранить гонку append-в-отвязанный-inode — каждый промах публикуется отдельным атомарно-переименованным файлом (os.replace tmp→уникальное имя по glob-шаблону), drain глобит все; потеря записи невозможна. Обновить _read_pending в тестах. 4. Все три канала (POSIX+PowerShell для #2) корректны. 5. Полная суита зелёная, 0 failed, 0 warnings.

## Plan

## Rollback

git revert; три независимых локальных изменения (условие матча флага, ведущая-тильда guard, схема файлов стока).

## Journal

- 2026-07-26T16:57:36Z [implementation] — AC verified: 1. ✓ test_hooks.py::TestInterpreterPayloadFlagMatch — decoy -ConfigurationName/-CustomPipeName before -Command no longer steal payload; -c/-Command/cmd /c//k still match. Match now 'command'.startswith(low[1:]) 2. ✓ test_hooks.py::test_command[rm_rf_dotslash_tilde_literal_allowed|rm_rf_nonleading_tilde_literal_allowed] exit 0; rm_rf_home_* still exit 2 — is_wipe_root leading-tilde guard 3. ✓ hook_supervision.py: each miss atomically published as own supervision_pending.<uniq>.jsonl via os.replace(tmp,final); drain globs published+claim, unique claim names; test_bypass_telemetry 50 passed incl orphan recovery + timestamp preservation 4. ✓ PowerShell channel shares is_wipe_root — leading-tilde fix covers both; test_powershell_channel green 5. ✓ tausik_verify high pytest PASS over 7 mapped files; hooks+telemetry+powershell+encoding 303 passed; nested-wrapper end-to-end still blocks; full-suite re-run pending pre-commit 6. ✓ Domain: reviewer-found HIGH (broken -Command extraction), MED (./~ false block), MED (lost-miss race) all closed; no live bypass reintroduced. Negative: powershell_echo/clean cases still allowed
