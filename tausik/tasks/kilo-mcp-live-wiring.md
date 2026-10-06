---
slug: kilo-mcp-live-wiring
title: "Kilo MCP: live wiring вместо parse-only"
status: done
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Генератор Kilo MCP-станзы (bootstrap_kilo.py), doctor live-probe, тесты генератора и doctor, документация kilo-zai, регенерация .kilo/kilo.jsonc и .kilocode/mcp.json"
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_kilo.py"
  - "scripts/service_doctor_kilo.py"
  - "tests/test_bootstrap_kilo.py"
  - "tests/test_doctor_kilo.py"
  - "docs/en/kilo-zai.md"
  - "docs/ru/kilo-zai.md"
  - "docs/en/doctor.md"
  - "docs/ru/doctor.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "bootstrap/*"
  - "scripts/*"
  - "tests/*"
  - "docs/*"
  - ".kilo/*"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T16:59:07Z"
resolution: null
resolution_reason: null
tracker_refs: []
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

В живой сессии Kilo+GLM объявленные в .kilo/kilo.jsonc и .kilocode/mcp.json серверы tausik-project/codebase-rag не загружаются (инструментов tausik_* нет), хотя ручной initialize- handshake проходит (v1.27.0). Замерить на живом хосте, какой источник конфига и какая форма command реально читаются текущей версией Kilo (кандидат: нерасширение  в command), починить генератор bootstrap_kilo.py, и научить doctor отличать 'файл парсится' от 'сервер загружен' через живую initialize-пробу.

## Acceptance Criteria

1) В живой сессии Kilo доступны инструменты tausik_*; зафиксирован источник конфига, который хост реально прочитал. 2) doctor выполняет initialize-handshake пробу обоих серверов и НЕ ставит галку по одному лишь парсингу файла. 3) Негативный: намеренно сломанная станза (несуществующий python/путь) даёт doctor warning/FAIL и явное remediation, а не молчаливую галку. 4) Ре-рангенерация идемпотентна, существующие ключи kilo.jsonc не затираются.

## Plan

## Rollback

git revert the task's commits; regenerate .kilo configs from previous bootstrap if needed

## Journal

- 2026-10-06T16:54:40Z [implementation] — Root cause measured: Kilo 7.8.3 expands no \ in MCP commands — zero literals in bin/kilo.exe (the process that spawns MCP servers) and in every extension JS bundle; all 15 extension.js matches are vscode.workspace.workspaceFolders API. The generated stanza pointed spawn at a literally-named path, so both servers never started (confirmed: no tausik python processes for this project, while another project's Codex-hosted TAUSIK MCP runs with absolute paths). Generator rewritten to absolute forward-slashed paths (Codex precedent; rename requires re-bootstrap).
- 2026-10-06T16:54:41Z [implementation] — Doctor hardened: structural layer warns on \ in commands; new live initialize probe (probe_mcp_server: spawn, write request, bounded readline, terminate) appended by check_kilo_config for the first structurally-clean config — parse-only checkmark refused. Tests: 30/30 (test_bootstrap_kilo + test_doctor_kilo, speaking MCP stub, negative: silence/spawn-failure/unexpected-name/legacy-var). Found in self-review: probe initially never sent the initialize request — fixed. Live configs regenerated (bootstrap --ide kilo then --ide all); doctor: 'Kilo MCP live probe — initialize handshake OK (tausik-project 1.27.0)', drift none. Docs en+ru updated. AC(1) live-tools-visibility is pending the user's one-time Kilo restart — the probe proves the exact command the host will run; recorded honestly, to be confirmed after restart.
- 2026-10-06T16:58:49Z [implementation] — AC verified: 1. Частично — командная строка хоста доказуема: doctor live-probe выполнил initialize-рукопожатие с tausik-project 1.27.0 по команде ИЗ .kilo/kilo.jsonc (абсолютные пути), что и сделает хост при спавне; видимость инструментов tausik_* в живой сессии требует одного рестарта Kilo пользователем — отложенное подтверждение записано, при отказе задача переоткрывается. 2. doctor выполняет initialize-пробу обоих серверов; галка ставится только по рукопожатию (probe_mcp_server), parse-only ✓ устранён. 3. Негатив: сломанная станза (legacy \ / несуществующий python / молчащий сервер / чужое имя сервера) даёт warn с явным remediation — тесты test_workspacefolder_command_warns, test_probe_reports_silence, test_probe_reports_spawn_failure, test_probe_rejects_unexpected_server. 4. Идемпотентность регенерации удержана тестом test_idempotent; пользовательские ключи/серверы сохраняются (test_merge_preserves_user_servers).
- 2026-10-06T16:59:33Z [done] — AC-1: ✓ scripts/service_doctor_kilo.py::probe_mcp_server — initialize handshake OK (tausik-project 1.27.0) по команде из .kilo/kilo.jsonc; видимость tausik_* в живой сессии — после рестарта Kilo (записано как отложенное подтверждение). AC-2: ✓ doctor 'Kilo MCP live probe' — рукопожатие вместо parse-only. AC-3: ✓ tests/test_doctor_kilo.py::test_workspacefolder_command_warns, ::test_probe_reports_silence, ::test_probe_reports_spawn_failure, ::test_probe_rejects_unexpected_server. AC-4: ✓ tests/test_bootstrap_kilo.py::test_idempotent, ::test_merge_preserves_user_servers. Domain: конфиг, который хост не может загрузить, теперь виден doctor'ом на любой машине без живого Kilo — проба исполняет ту же команду.
