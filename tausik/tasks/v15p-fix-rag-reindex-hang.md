---
slug: v15p-fix-rag-reindex-hang
title: "[P0] Defect: зависание переиндексации codebase-rag"
status: done
epic: v15-polish
story: v15p-defects
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "harness/*/mcp/codebase-rag/ (server.py, rag_indexer.py), tests/"
scope_exclude: null
relevant_files:
  - CLAUDE.md
  - "harness/claude/mcp/codebase-rag/rag_indexer.py"
  - "harness/claude/mcp/codebase-rag/rag_detect.py"
  - "harness/claude/mcp/codebase-rag/server.py"
  - "harness/cursor/mcp/codebase-rag/rag_indexer.py"
  - "harness/cursor/mcp/codebase-rag/rag_detect.py"
  - "harness/cursor/mcp/codebase-rag/server.py"
  - "tests/test_rag_reindex_hang.py"
  - "tests/test_rag_reindex_progress.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-11T23:38:44Z"
---

## Goal

Воспроизвести и устранить зависание reindex в codebase-rag MCP (harness/*/mcp/codebase-rag/server.py + rag_indexer.py). Анализ: subprocess-блокировки на Windows (ср. memory #24: git subprocess hang, лечился прямым чтением .git/HEAD + asyncio.to_thread), отсутствие timeout-envelope, прогресс-репортинг. AC: hang воспроизведён и задокументирован root cause; reindex завершается или падает с явной ошибкой за бюджет времени (timeout + cancel); регрессионный тест; фикс в обоих harness (claude+cursor).

## Acceptance Criteria

1. Hang воспроизведён и root cause задокументирован в task log. 2. reindex завершается или падает с явной ошибкой за бюджет времени (timeout + cancel, без вечного зависания). 3. Регрессионный тест на timeout-сценарий добавлен и зелёный. 4. Фикс применён в обоих harness (claude + cursor) через исходники в harness/.

## Plan

## Rollback

## Journal

- 2026-06-11T23:20:29Z [implementation] — Анализ кода: claude/cursor копии идентичны (fc /B). Кандидаты на root cause: (1) get_file_list — os.walk без time-budget и без защиты от Windows junction-циклов (os.walk не считает junction симлинком → follow → бесконечный обход); (2) RAGStore без busy_timeout — конкурентный lock даёт OperationalError через 5с, но store.clear() с FTS-триггером per-row на больших индексах может работать минуты; (3) server.py call_tool: asyncio.to_thread без asyncio.wait_for → любое зависание _sync_call_tool висит вечно на уровне MCP; (4) max_seconds не применяется по умолчанию (None) и не покрывает фазу get_file_list. Перехожу к воспроизведению standalone-драйвером с watchdog.
- 2026-06-11T23:23:23Z [implementation] — ROOT CAUSE ВОСПРОИЗВЕДЁН (d:\tmp\rag_repro\repro_git_hang.py): subprocess.run(git diff, capture_output=True, timeout=3) на Windows зависает НАВСЕГДА, если git породил долгоживущего внука с унаследованным stdout-хэндлом (git fsmonitor--daemon, credential helper, git.exe-шим). Механизм: communicate(timeout=3) ловит TimeoutExpired (EOF не приходит — pipe держит внук), CPython вызывает proc.kill() + ВТОРОЙ communicate() БЕЗ таймаута → вечная блокировка. Репро: 20s watchdog — процесс жив, вывод только 'calling subprocess.run...'. Дополнительно: junction-цикл в os.walk даёт 64x амплификацию (не вечный hang, MAX_PATH обрезает); get_file_list без time-budget; server.py без hard timeout вокруг to_thread. План фикса: (1) _get_changed_files → Popen + ручной TimeoutExpired-handling без второго communicate (kill + close pipes, reader-threads daemon); (2) index_full: max_seconds default 300; (3) server.py: asyncio.wait_for hard envelope вокруг reindex; (4) регрессионный тест с fake-git внуком.
- 2026-06-11T23:30:17Z [implementation] — Фикс реализован: (1) rag_indexer._run_git — Popen с ручным TimeoutExpired-handling, БЕЗ второго блокирующего communicate (kill + wait(1) + abandon daemon reader threads); _get_changed_files переведён на _run_git; (2) index_full: max_seconds default 300 (DEFAULT_MAX_SECONDS), None = explicit opt-out; (3) rag_detect.get_file_list: параметр max_seconds (deadline в os.walk) + пропуск junction/symlink-директорий (_is_reparse_or_symlink, FILE_ATTRIBUTE_REPARSE_POINT 0x400); (4) server.py: asyncio.wait_for hard envelope вокруг каждого tool call (_tool_timeout_sec: reindex = soft+60s, остальные 120s), явная ошибка вместо вечного hang; отсутствующий max_seconds больше не передаётся как None (не отключает бюджет). Тесты: tests/test_rag_reindex_hang.py — 14 новых (fake-git с внуком-держателем pipe, deadline, junction-цикл, envelope); фикстура test_rag_reindex_progress поправлена под новую сигнатуру. 83 passed по всему RAG-сьюту. Cursor-harness синхронизирован (fc /B identical), bootstrap перегенерировал .claude. Smoke: 631 файл / 6710 чанков / 2.7s.
- 2026-06-11T23:30:38Z [implementation] — AC verified: 1. ✓ Hang воспроизведён standalone (d:/tmp/rag_repro/repro_git_hang.py, 20s watchdog): subprocess.run(timeout=3) виснет навечно при внуке с унаследованным stdout-pipe; root cause задокументирован в task log 2. ✓ index_full default max_seconds=300 + deadline в get_file_list + asyncio.wait_for hard envelope в server.call_tool (явная ошибка вместо hang) 3. ✓ tests/test_rag_reindex_hang.py — 14 тестов, в т.ч. test_run_git_survives_pipe_holding_grandchild (wall-clock < 7s); 83 passed весь RAG-сьют 4. ✓ harness/cursor синхронизирован (fc /B no differences), bootstrap перегенерировал .claude
- 2026-06-11T23:31:01Z [implementation] — AC verified: 1. ✓ Hang воспроизведён standalone (d:/tmp/rag_repro/repro_git_hang.py, 20s watchdog): subprocess.run(timeout=3) виснет навечно при внуке с унаследованным stdout-pipe; root cause задокументирован в task log 2. ✓ index_full default max_seconds=300 + deadline в get_file_list + asyncio.wait_for hard envelope в server.call_tool (явная ошибка вместо hang) 3. ✓ tests/test_rag_reindex_hang.py — 14 тестов, в т.ч. test_run_git_survives_pipe_holding_grandchild (wall-clock < 7s); 83 passed весь RAG-сьют 4. ✓ harness/cursor синхронизирован (fc /B no differences), bootstrap перегенерировал .claude
- 2026-06-11T23:32:50Z [implementation] — AC verified: 1. ✓ Hang воспроизведён standalone (d:/tmp/rag_repro/repro_git_hang.py, 20s watchdog): subprocess.run(timeout=3) виснет навечно при внуке с унаследованным stdout-pipe; root cause задокументирован в task log 2. ✓ index_full default max_seconds=300 + deadline в get_file_list + asyncio.wait_for hard envelope в server.call_tool (явная ошибка вместо hang) 3. ✓ tests/test_rag_reindex_hang.py — 14 тестов, в т.ч. test_run_git_survives_pipe_holding_grandchild (wall-clock < 7s); 83 passed весь RAG-сьют 4. ✓ harness/cursor синхронизирован (fc /B no differences), bootstrap перегенерировал .claude
- 2026-06-11T23:38:44Z [implementation] — AC verified: 1. ✓ Hang воспроизведён standalone-репро (subprocess.run+timeout виснет навечно при внуке-держателе pipe), root cause в task log. 2. ✓ index_full default max_seconds=300, deadline в get_file_list, asyncio.wait_for hard envelope в server.call_tool. 3. ✓ tests/test_rag_reindex_hang.py: 14 тестов, 83 passed весь RAG-сьют. 4. ✓ cursor-harness идентичен (fc /B), bootstrap перегенерирован.
