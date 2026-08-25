---
slug: v156-p1-windows-unicode
title: "P1: Windows/Unicode — враппер ставит PYTHONUTF8=1; аудит fix_stdio_encoding() во всех entry points"
status: done
epic: v156
story: v156-kilo-zai-finetune
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "bootstrap/tausik_wrapper.sh, bootstrap/tausik_wrapper.cmd, bootstrap/bootstrap_generate.py (_hook_cmd), bootstrap/bootstrap.py (main), harness/*/mcp/*/server.py (entry), scripts/tausik_utils.py (если нужна правка), tests/ (новый тест)"
scope_exclude: ".claude/ и прочие сгенерированные копии; 24 отдельных файла хуков (покрываются через -X utf8, не правим каждый)"
relevant_files:
  - "bootstrap/tausik_wrapper.sh"
  - "bootstrap/tausik_wrapper.cmd"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap.py"
  - "harness/claude/mcp/project/server.py"
  - "harness/claude/mcp/brain/server.py"
  - "harness/claude/mcp/codebase-rag/server.py"
  - "harness/cursor/mcp/project/server.py"
  - "harness/cursor/mcp/brain/server.py"
  - "harness/cursor/mcp/codebase-rag/server.py"
  - "tests/test_unicode_stdio.py"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T19:21:45Z"
---

## Goal

Устранить UnicodeEncodeError на Windows (cp1251 stdout). Враппер (.sh/.cmd) экспортирует PYTHONUTF8=1 перед вызовом python. Аудит: ВСЕ entry points (scripts/hooks/*.py, MCP-серверы, bootstrap) зовут fix_stdio_encoding() из scripts/tausik_utils.py. Тест: cp1251 stdout без UnicodeEncodeError.

## Acceptance Criteria

1. Враппер .sh (export) и .cmd (set) выставляют PYTHONUTF8=1 перед вызовом python — все CLI-инвокации получают UTF-8 stdio. 2. _hook_cmd (bootstrap_generate.py) генерирует команду `python -X utf8 <hook>`, так что ВСЕ хуки (24 шт., у которых нет общего раннера) получают UTF-8 mode из одной точки; то же для qwen/cursor settings, если они используют отдельный билдер. 3. Standalone entry points вне враппера зовут fix_stdio_encoding() из tausik_utils: bootstrap.py (заменить инлайн reconfigure), MCP-серверы (harness/*/mcp/*/server.py) — добавить, если отсутствует. 4. Регрессионный тест: запуск процесса, печатающего Unicode (✓/кириллица) в stdout под cp1251-локалью, БЕЗ UTF-8 → воспроизводит UnicodeEncodeError; С fix_stdio_encoding()/PYTHONUTF8/-X utf8 → exit 0, вывод корректен. 5. НЕГАТИВНЫЙ: при отсутствии reconfigure-атрибута у потока (не-Windows / уже-обёрнутый stream) fix_stdio_encoding() не падает (no-op).

## Plan

[{"step": "\u0410\u0443\u0434\u0438\u0442 entry points: fix_stdio_encoding \u0442\u043e\u043b\u044c\u043a\u043e \u0432 project.py; 24 \u0445\u0443\u043a\u0430/6 MCP/bootstrap \u043d\u0435 \u0437\u043e\u0432\u0443\u0442", "done": true}, {"step": "\u0412\u0440\u0430\u043f\u043f\u0435\u0440 .sh/.cmd: export/set PYTHONUTF8=1 \u043f\u0435\u0440\u0435\u0434 python", "done": true}, {"step": "_hook_cmd \u00d72 (claude+qwen): python -X utf8 <hook> \u2014 \u043f\u043e\u043a\u0440\u044b\u0432\u0430\u0435\u0442 \u0432\u0441\u0435 24 \u0445\u0443\u043a\u0430 \u0438\u0437 \u043e\u0434\u043d\u043e\u0439 \u0442\u043e\u0447\u043a\u0438", "done": true}, {"step": "bootstrap.py main(): \u0438\u043d\u043b\u0430\u0439\u043d reconfigure \u2192 fix_stdio_encoding()", "done": true}, {"step": "6 MCP server.py (3 canonical claude + 3 cursor-\u043a\u043e\u043f\u0438\u0438): fix_stdio_encoding() \u0432 \u043d\u0430\u0447\u0430\u043b\u0435 main()", "done": true}, {"step": "\u0420\u0435\u0433\u0440\u0435\u0441\u0441\u0438\u043e\u043d\u043d\u044b\u0439 \u0442\u0435\u0441\u0442 test_unicode_stdio.py: repro cp1251-\u043a\u0440\u0430\u0448 + 3 \u0444\u0438\u043a\u0441\u0430 + wiring-\u0430\u0441\u0441\u0435\u0440\u0442\u044b", "done": true}, {"step": "\u0420\u0435\u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044f doc-constants + README EN/RU test_count, \u043f\u0440\u043e\u0433\u043e\u043d \u0441\u044c\u044e\u0442\u044b", "done": true}]

## Rollback

git revert — изменения изолированы в bootstrap/ + harness/ + tests/. PYTHONUTF8/-X utf8 аддитивны (не ломают существующее поведение на UTF-8 системах).

## Journal

- 2026-06-19T19:21:45Z [implementation] — AC verified: AC-1: ✓ враппер .sh `export PYTHONUTF8=1` / .cmd `set "PYTHONUTF8=1"` перед python — test_wrappers_set_pythonutf8 PASSED; empirically PYTHONUTF8=1 фиксит cp1252-краш (test_locale_default_crashes_then_pythonutf8_fixes_it PASSED, win32). AC-2: ✓ _hook_cmd (bootstrap_generate.py + bootstrap_qwen.py) → `python -X utf8 <hook>` — test_hook_command_builders_use_x_utf8 PASSED; -X utf8 фиксит locale default (test_x_utf8_flag_fixes_locale_default PASSED). AC-3: ✓ bootstrap.py main()→fix_stdio_encoding() (test_bootstrap_uses_fix_stdio_encoding); 6 MCP server.py (3 canonical claude + 3 cursor sync) зовут fix_stdio_encoding() в main() — test_mcp_servers_call_fix_stdio_encoding PASSED, py_compile все 6 OK. AC-4: ✓ repro: PYTHONIOENCODING=cp1251 + Unicode → UnicodeEncodeError exit≠0 (test_cp1251_stdout_crashes_without_fix); fix_stdio_encoding() reconfigure → exit 0 даже поверх cp1251 (test_fix_stdio_encoding_overrides_locale, win32). AC-5: ✓ НЕГАТИВНЫЙ: fix_stdio_encoding() с подменённым stdout без reconfigure-атрибута/не-win32 не падает (test_fix_stdio_encoding_is_safe_to_call). Domain: воспроизведено на реальной cp1252-Windows (машина юзера = Russian Windows, тот же класс бага). test_unicode_stdio.py 9/9 PASSED; полный связанный сьют 582 passed после регенерации doc-constants+README (4401→4416). Примечание: хуки покрыты через -X utf8 (24 файла, нет общего раннера) — единая точка вместо 24 правок.
