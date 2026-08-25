---
slug: v2-stale-mcp-reaping
title: "Реапинг stale-MCP серверов (или единый демон) — убивает класс drift/hang #77/#79/#80"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: ".tausik/tausik.db actual-process-killing:no-auto-kill-mechanism"
relevant_files:
  - "scripts/mcp_reaper.py"
  - "tests/test_mcp_reaper.py"
  - "harness/claude/mcp/project/self_check.py"
  - "tests/test_mcp_self_check.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/mcp_reaper.py"
  - "tests/test_mcp_reaper.py"
  - "harness/claude/mcp/project/self_check.py"
  - "tests/test_mcp_self_check.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-27T15:35:54Z"
---

## Goal

Перезагрузка IDE не реапит старые MCP-серверы — наблюдалось 17 живых python-процессов в 3 генерациях, каждый держит WAL-коннект к одной tausik.db. Это корень recurring «MCP будто завис/дрейфит». Реапинг по PID-файлу при спавне ИЛИ переход на единый демон (см. v2-mcp-request-time-db-routing).

## Acceptance Criteria

AC1. Принято решение владельца по развилке (tausik decide): auto-reap при спавне vs явная команда reap + жёсткое предупреждение при sibling_count>N — с учётом того, что живые сиблинг-сессии одного окна не отличить от протухших по дереву процессов.
AC2. Реализован выбранный механизм: stale MCP-процессы реапятся или сообщаются, но живые сиблинг-сессии одного окна Code.exe НЕ убиваются — проверка на дереве процессов (positive+negative).
AC3. self_check._enumerate_sibling_mcps не поднимает свежий powershell Get-CimInstance на КАЖДЫЙ вызов на Win11 26200 (wmic удалён из образа): энумерация 100+ процессов больше не делает /start похожим на зависание — замер времени до/после.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; changes are additive (new scripts/mcp_reaper.py) + TTL-cache wrapper in self_check enumeration + report-only warning string. No process is ever killed by the framework, so no destructive action to undo.

## Journal

- 2026-07-18T08:56:36Z [planning] — СВЕЖИЙ ЭВИДЕНС 2026-07-17/18 (форензика живой машины, Win11 build 26200): 104 python-процесса, 54 из них MCP server.py; для ЭТОГО проекта 12 процессов = 6 пар (venv-launcher + интерпретатор) tausik-project серверов. ВАЖНО: осиротевших НЕТ — каждая пара висит под ЖИВЫМ claude.exe, и все 6 claude.exe принадлежат ОДНОМУ окну Code.exe (PID 7460, возраст 5ч). То есть корень не 'IDE не реапит при рестарте', а НАКОПЛЕНИЕ claude-code сессий внутри одного окна: каждая новая сессия плодит пару, старые живут пока жив их claude.exe. Перезагрузка IDE окно 7460 не затронула (оно 313 мин). Усугубление на Win11 26200: wmic УДАЛЁН из образа, поэтому self_check._enumerate_sibling_mcps на КАЖДЫЙ вызов поднимает свежий powershell Get-CimInstance (~0.6-1с при энумерации 100+ процессов) — это и делало /start похожим на зависание. ДИЗАЙН-РАЗВИЛКА (нужно решение владельца): auto-reap при спавне рискует убить ЖИВЫЕ сиблинг-сессии в том же окне (их не отличить от протухших по дереву процессов) vs явная команда reap + жёсткое предупреждение при sibling_count>N. Дубль-задача mcp-session-leak удалена, эвиденс здесь.
- 2026-07-18T13:25:20Z [planning] — ПЕРЕЖИВАЕТ ОТМЕНУ 2.0 (решение 2026-07-18). Эпик v2-global-mcp отменён, но эта задача ценна независимо от него и остаётся в работе. Для gmcp-packaging причина прямая: pip-пакет с entry-points делает .mcp.json коммитабельным (ссылка на tausik-mcp в PATH вместо абсолютного пути к интерпретатору), а это предпосылка командной работы из нового эпика shared-knowledge.
- 2026-07-27T15:35:53Z [implementation] — AC1 (design fork): decision #189 recorded — REPORT + hard threshold warning, NO in-framework killing; live siblings can't be told from stale by process tree, so any auto-killer risks data loss. AC2: mcp_reaper.sibling_warning() surfaces a report-only 'close old sessions' warning above threshold (states framework will NOT kill), wired into self_check.collect() as report['sibling_warning'] + prepended to remediation; tests/test_mcp_self_check.py::test_sibling_count_over_threshold_reports_warning (positive) + test_sibling_count_within_threshold_no_warning (negative) + test_mcp_reaper.py::TestSiblingWarning. AC3: enumeration TTL-cached (mcp_reaper.cached_enumerate, 30s, process-scoped) via _enumerate_sibling_mcps_cached — no fresh PowerShell Get-CimInstance per call; test_sibling_enumeration_is_ttl_cached asserts enum runs once across two collect() calls + TestCachedEnumerate TTL/isolation cases. CHANGELOG: prose entry EN+RU. Negative: within-threshold + introspection-failure(-1) + non-int all silent (tested). Domain: on real Win11 26200 the wmic path always falls through to PowerShell; caching removes the ~1s-per-call hang that made /start look stuck, without ever killing a live session. Full scoped verify green (run #1512, signed).
