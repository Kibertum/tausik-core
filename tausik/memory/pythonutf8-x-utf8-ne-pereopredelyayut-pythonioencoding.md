---
slug: pythonutf8-x-utf8-ne-pereopredelyayut-pythonioencoding
title: "PYTHONUTF8/-X utf8 НЕ переопределяют PYTHONIOENCODING; runtime reconfigure — да"
type: gotcha
tags:
  - gotcha
  - pythonutf8
  - stdio
  - unicode
  - v156
  - windows
task: v156-p1-windows-unicode
edges: []
---

Windows-краш UnicodeEncodeError при печати Cyrillic/✓ возникает из-за locale-кодировки stdout (cp1251/cp1252). Иерархия фиксов (проверено эмпирически на cp1252-Windows, v156 P1):
- PYTHONUTF8=1 и `python -X utf8` фиксят ТОЛЬКО locale default. Если выставлен PYTHONIOENCODING=cp1251 — он имеет высший приоритет, UTF-8 mode его НЕ переопределяет → краш остаётся.
- fix_stdio_encoding() (scripts/tausik_utils.py) делает sys.stdout/stderr.reconfigure(encoding='utf-8', errors='replace') в рантайме — переопределяет ВСЁ, включая PYTHONIOENCODING. Но guard `if sys.platform=='win32'` → на Linux no-op.
Поэтому слои не взаимозаменяемы: враппер ставит PYTHONUTF8 (CLI), хуки идут через -X utf8 (запускаются напрямую, не через враппер — нет общего раннера, инжект в _hook_cmd ×2: bootstrap_generate.py + bootstrap_qwen.py), а standalone entry points (bootstrap.py, 6 MCP server.py) дополнительно зовут fix_stdio_encoding() как defense-in-depth.
Тест-репро: PYTHONIOENCODING=cp1251 + print('✓') воспроизводит краш кросс-платформенно; проверка -X utf8/PYTHONUTF8 требует non-UTF8 locale default → win32-only (tests/test_unicode_stdio.py).
