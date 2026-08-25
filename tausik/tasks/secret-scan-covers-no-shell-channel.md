---
slug: secret-scan-covers-no-shell-channel
title: "secret_scan не покрывает ни один оболочечный канал: секрет, записанный heredoc'ом или Set-Content, не сканируется"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/secret_scan.py, bootstrap/bootstrap_hooks.py, bootstrap/bootstrap_qwen.py, tests/test_secret_scan_hook.py, docs/ru/agent-contract.md (+ docs/en если есть)"
scope_exclude: null
relevant_files:
  - "scripts/hooks/secret_scan.py"
  - "scripts/hooks/rm_wipe_detect.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "tests/test_secret_scan_hook.py"
  - "tests/test_hooks.py"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T15:54:01Z"
---

## Goal

Найдено при построении матрицы покрытия каналов в powershell-tool-bypasses-bash-firewall. `secret_scan.py` (SENAR Rule 10.12) зарегистрирован на matcher `Write|Edit|MultiEdit`. Оболочечные инструменты — ни Bash, ни PowerShell — не покрыты вообще. То есть `cat > .env <<EOF` с AWS-ключом внутри и `Set-Content -Path .env -Value 'AKIA...'` пишут ровно то содержимое, которое хук отказался бы пропустить через Write.

Это НЕ перекос между каналами, а равный пробел в обоих — поэтому он сознательно оставлен вне задачи про PowerShell: закрыть его на одной оболочке значило бы снова развести каналы, что и было её главным дефектом. Пробел объявлен явно в матрице docs/*/agent-contract.md, но объявление — не закрытие.

Механика для закрытия уже есть и переиспользуема: `shell_channel.write_targets_with_confidence(tool_name, command)` даёт цели записи в обоих диалектах, а bash_write_gate показывает образец «тот же вердикт, что у Write, переиспользованием его решения, а не копией». Нужное здесь отличие: secret_scan судит СОДЕРЖИМОЕ, а не путь, поэтому для оболочки надо извлечь записываемое ЗНАЧЕНИЕ (тело heredoc, -Value у Set-Content/Add-Content, конвейерный вход у Out-File), и вот тут остаточная граница будет шире, чем у путей: значение из переменной не резолвится.

Обязательно взвесить цену ошибки (конв. #291): secret_scan по умолчанию WARN, а не блок, поэтому ложное срабатывание дешевле, чем у memory_pretool_block, — но под TAUSIK_SECRET_SCAN_STRICT=1 он блокирует, и там цена другая.

## Acceptance Criteria

1. secret_scan срабатывает на оболочечных каналах (Bash + PowerShell), симметрично — секрет в heredoc (`cat > .env <<EOF ... AKIA... EOF`) и в `Set-Content -Value 'AKIA...'` детектится. 2. Механизм: хук зарегистрирован на SHELL_MATCHER в ОБОИХ bootstrap (main+qwen), внутренний guard пропускает shell-инструменты через shell_channel.is_shell_tool (без литерального списка — конв. #289). 3. Дефолтный WARN сохранён, TAUSIK_SECRET_SCAN_STRICT=1 блокирует и на оболочке. 4. Секрет, переданный через переменную/env (не литерал), НЕ флагается (документированный остаток). 5. Read/не-write не-shell по-прежнему игнорируются. 6. Матрица покрытия каналов в docs/*/agent-contract.md обновлена (пробел закрыт). 7. Профили переразвёрнуты; полная суита зелёная, 0 warnings.

## Plan

## Rollback

git revert; изменение сводится к добавлению SHELL_MATCHER в matcher секрет-скана и снятию guard-ограничения на tool_name — откат восстанавливает Write-only поведение.

## Journal

- 2026-07-26T15:53:59Z [implementation] — AC verified: 1. ✓ test_secret_scan_hook.py::test_bash_heredoc_secret_warns + test_powershell_set_content_secret_warns — symmetric across both dialects 2. ✓ bootstrap_hooks.py+bootstrap_qwen.py secret_scan matcher = Write|Edit|MultiEdit|SHELL_MATCHER; guard uses shell_channel.is_shell_tool; test_bootstrap_hooks_parity green 3. ✓ default WARN: test_bash_export_literal_warns rc=0; strict: test_shell_strict_mode_blocks rc=2 4. ✓ test_shell_secret_via_variable_not_flagged — $TOKEN not flagged (stated residual) 5. ✓ test_non_write_tool_ignored (Read) unchanged; test_clean_shell_command_passes 6. ✓ docs/en+ru/enforcement-coverage.md matrix row secret_scan updated ❌→✅ with footnote #178 7. ✓ bootstrap redeployed all 5 profiles; tausik_verify high pytest PASS over 4 mapped files (secret_scan, bootstrap parity, qwen, hooks); constants regenerated 8. ✓ Domain: a real AWS key literal in a heredoc/Set-Content/export is caught pre-write across Bash+PowerShell; env-var indirection correctly passes — behaviour valid on real shell inputs
