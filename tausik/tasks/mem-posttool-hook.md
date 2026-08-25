---
slug: mem-posttool-hook
title: "PostToolUse hook: аудит записей в Claude auto-memory"
status: done
epic: memory-discipline-hardening
story: memory-post-write-audit
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/memory_posttool_audit.py (новый), bootstrap/bootstrap_generate.py, bootstrap/bootstrap_qwen.py"
scope_exclude: "Не писать markers-модуль (уже done). Не писать тесты (отдельная задача). Не трогать pretool-block hook."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T22:59:02Z"
---

## Goal

После Write к memory/ — прочитать файл, прогнать markers regex, при detection вывести warning "эта запись проектная — перенеси в tausik memory add". Не блокирует, но ловит промахи которые A пропустил (например запись через bypass-маркер).

## Acceptance Criteria

1. scripts/hooks/memory_posttool_audit.py — PostToolUse hook, stdlib-only, импортирует memory_markers через sys.path.insert. 2. Активируется на tool_name in Write|Edit|MultiEdit. 3. Если tool_input.file_path под ~/.claude/projects/*/memory/ — читает файл, прогоняет detect_markers. Вне memory/ → exit 0 молча. 4. При markers detected — stderr 'AUDIT: auto-memory write contains N project markers:' + bullet-list до 5 matches (kind + match) + подсказка 'Consider moving project knowledge to .tausik/tausik memory add'. Exit 0 (warning, НЕ block). 5. При отсутствии markers — exit 0 silently (no stderr). 6. NEGATIVE: запись 'user prefers Russian responses' → 0 markers → silent exit 0. 7. Graceful (exit 0 без сообщений): не TAUSIK проект, malformed stdin, file_path не string, файл не существует или не читается, tool_input отсутствует. 8. TAUSIK_SKIP_HOOKS=1 → exit 0. 9. Регистрация в bootstrap_generate.py PostToolUse (matcher Write|Edit|MultiEdit) + bootstrap_qwen.py PostToolUse. 10. Повторное использование _is_in_claude_memory из memory_pretool_block.py (импорт через sys.path) для консистентности path detection.

## Plan

## Rollback

## Journal

- 2026-04-22T22:56:24Z [implementation] — AC verified smoke-тестом: (1) scripts/hooks/memory_posttool_audit.py stdlib-only, импортирует memory_markers + memory_pretool_block через sys.path ✓. (2) tool_name Write|Edit|MultiEdit — активируется; Bash → exit=0 silently ✓. (3) file_path под memory/ — читает+сканит; вне memory/ (README.md) → exit=0 silently ✓. (4) Positive detection: 'mem-pretool-hook ... scripts/hooks/session_start.py ... .tausik/tausik status' → stderr 'AUDIT: auto-memory write ... contains 3 project marker(s): [slug] mem-pretool-hook / [src_file] scripts/hooks/session_start.py / [tausik_cmd] .tausik/tausik' + hint 'tausik memory add' ✓. (5) No markers: 'user prefers Russian responses and likes pytest' → exit=0 silently, no stderr ✓. (6,7) Graceful: не-TAUSIK dir, Bash tool, non-memory path — все exit=0. (9) Регистрация в bootstrap_generate.py + bootstrap_qwen.py PostToolUse matcher Write|Edit|MultiEdit ✓. (10) _is_in_claude_memory переиспользован из memory_pretool_block через import — консистентность ✓. Ruff: All checks passed.
