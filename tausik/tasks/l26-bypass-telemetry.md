---
slug: l26-bypass-telemetry
title: "Телеметрия обходов: сейчас выключение надзора молчаливо"
status: done
epic: landscape-2026-h2
story: l26-provable
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/_common.py (+хелпер), scripts/hooks/{task_gate,scope_write_gate,bash_firewall,secret_scan,task_done_verify,task_cost_budget_check,git_push_gate}.py, scripts/gate_verify_first.py, scripts/risk_l3_trigger.py, scripts/gate_qg0_check.py, scripts/gate_toggle.py, scripts/backend_queries_metrics.py, scripts/project_cli_metrics.py|project_cli_ops.py (render), tests/ (новые тесты)"
scope_exclude: "harness/opencode/plugins/tausik-qg0.js (parity вынесен отдельной задачей), не-enforcement nudge-хуки (auto_format, keyword_detector, session_start и т.п.), backend_schema.py/миграции (без изменений схемы — events уже существует)"
relevant_files:
  - "scripts/hooks/_common.py"
  - "scripts/hooks/task_gate.py"
  - "scripts/hooks/scope_write_gate.py"
  - "scripts/hooks/bash_firewall.py"
  - "scripts/hooks/secret_scan.py"
  - "scripts/hooks/task_done_verify.py"
  - "scripts/hooks/task_cost_budget_check.py"
  - "scripts/hooks/git_push_gate.py"
  - "scripts/gate_verify_first.py"
  - "scripts/risk_l3_trigger.py"
  - "scripts/gate_qg0_check.py"
  - "scripts/service_gates.py"
  - "scripts/gate_toggle.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/project_cli_metrics.py"
  - "tests/test_bypass_telemetry.py"
scope_paths:
  - "scripts/hooks/_common.py"
  - "scripts/hooks/task_gate.py"
  - "scripts/hooks/scope_write_gate.py"
  - "scripts/hooks/bash_firewall.py"
  - "scripts/hooks/secret_scan.py"
  - "scripts/hooks/task_done_verify.py"
  - "scripts/hooks/task_cost_budget_check.py"
  - "scripts/hooks/git_push_gate.py"
  - "scripts/gate_verify_first.py"
  - "scripts/risk_l3_trigger.py"
  - "scripts/gate_qg0_check.py"
  - "scripts/service_gates.py"
  - "scripts/gate_toggle.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_cli_ops.py"
  - "tests/test_bypass_telemetry.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-21T09:33:26Z"
---

## Goal

Все способы ослабить систему НЕ ОСТАВЛЯЮТ СЛЕДА: переменные окружения TAUSIK_SKIP_HOOKS и TAUSIK_SKIP_PUSH_HOOK, конфиг-ключи auto_verify=true, l3_block_on_high=false, scope_hard_gate=false, вызов gates_disable. Система не может сообщить, сколько раз её выключали — а значит любые заявления о принуждении неопровержимы и неподтверждаемы. Нужно: писать событие в events на каждое срабатывание обхода (кто, что, когда, чем именно ослаблено), плюс счётчик в metrics. Это дешевле, чем закрывать все обходы, и честнее, чем молчать. Смежно: нет счётчиков вызова хуков — миswired хук (неверный абсолютный путь к python после переезда машины) падает молча и выглядит идентично нечего блокировать.

## Acceptance Criteria

AC1: Общий chain-safe хелпер эмиссии для хук-подпроцессов в scripts/hooks/_common.py (напр. emit_supervision_bypass(project_dir, vector, details=None)): raw INSERT INTO events(entity_type='supervision', entity_id=<vector>, action='bypass_<vector>', details); best-effort в try/except — НИКОГДА не роняет хук; сам НЕ читает TAUSIK_SKIP_HOOKS (иначе подавит собственный аудит). DB через CLAUDE_PROJECT_DIR|cwd + .tausik/tausik.db.
AC2: Инструментированы 6 векторов обхода из goal — каждый эмитит событие ПЕРЕД ослаблением: (a) TAUSIK_SKIP_HOOKS в enforcement-хуках task_gate/scope_write_gate/bash_firewall/secret_scan/task_done_verify/task_cost_budget_check; (b) TAUSIK_SKIP_PUSH_HOOK в git_push_gate; (c) auto_verify=true в gate_verify_first; (d) l3_block_on_high=false в risk_l3_trigger (raw conn.execute — есть conn); (e) scope_hard_gate=false в gate_qg0_check; (f) gates_disable в gate_toggle.set_gate_enabled (единый chokepoint CLI+MCP+brain). Service-слой использует svc.be.event_add(...).
AC3: Метрика supervision_bypasses в get_metrics() (backend_queries_metrics.py) агрегатом SELECT action,COUNT(*) FROM events WHERE entity_type='supervision' GROUP BY action; отрендерена в выводе tausik metrics.
AC4: Chain-safe: raw INSERT оставляет entry_hash NULL, запечатывается лениво events_seal — negative-тест: events_verify зелёный после серии эмиссий.
AC5: Тесты по каждому вектору: обход пишет РОВНО одно событие supervision/bypass_*; metrics считает; телеметрия fail-open (симулированная ошибка записи не роняет хук/гейт). Full suite зелёный.
AC6: Смежные находки (opencode JS tausik-qg0.js parity, TAUSIK_SKIP_MEMORY_HOOK, docstring-mismatch memory_pretool_block, fail-open DB-точки task_gate/scope_write_gate) вынесены отдельными planning-задачами, а не молча проигнорированы.

## Plan

## Rollback

git revert коммита — все изменения аддитивны (новый хелпер + вызовы эмиссии + один агрегат в метриках); удаление вызовов и метрик-ключа возвращает прежнее поведение, схема БД не менялась, данные событий безвредны (лишние строки в events безобидны).

## Journal

- 2026-07-21T08:52:33Z [implementation] — Реализация завершена. 6 векторов инструментированы: (1) TAUSIK_SKIP_HOOKS в 6 enforcement-хуках через новый _common.emit_supervision_bypass (raw chain-safe INSERT, best-effort, не читает SKIP_HOOKS сам); (2) TAUSIK_SKIP_PUSH_HOOK в git_push_gate; (3) auto_verify в gate_verify_first (svc.be.event_add); (4) l3_block_on_high=false в risk_l3_trigger (raw conn, свой try/except чтобы не подавить WARNING, без commit — на транзакции потока); (5) scope_hard_gate=false через колбэк check_qg0_start←service_gates (без дублирования условия); (6) gates_disable в gate_toggle.set_gate_enabled (единый chokepoint, эмит ТОЛЬКО при реальном effective-disable, не при trust-отклонении). Метрика supervision_bypasses в get_metrics (on-the-fly GROUP BY action) + рендер в project_cli_metrics (только при total>0). Тесты tests/test_bypass_telemetry.py: 19 passed — helper (row/no-db/broken-db/не-читает-SKIP), chain-safety (events_verify ok), метрика, gates_disable (emit/enable-no-emit/rejected-no-emit), l3 (downgrade-emit/block-no-emit), scope_hard_gate (callback/raise/simple), auto_verify, hook subprocess end-to-end (bash_firewall+git_push_gate emit on skip, no-skip no-emit). AC6: 3 follow-up заведены (opencode-parity, memory_pretool_block toggle+docstring, hook-fail-open-db-error). Далее: bootstrap --ide all + full suite + verify + done.
- 2026-07-21T09:31:50Z [implementation] — АДВЕРСАРИАЛЬНОЕ РЕВЬЮ (tausik-reviewer, отдельная модель) нашло 3 РЕАЛЬНЫХ дефекта, все исправлены + покрыты регресс-тестами: [CRITICAL] risk_l3_trigger: raw INSERT без commit на общем conn оставлял открытую implicit-транзакцию → следующий begin_tx() BEGIN IMMEDIATE в service_task_done крашил закрытие high-risk задач при l3_block_on_high=false ('cannot start a transaction within a transaction'). Фикс: _emit_l3_downgrade на ОТДЕЛЬНОМ короткоживущем соединении (commit+close), путь к БД из PRAGMA database_list. Регресс-тест test_downgrade_leaves_no_open_transaction: после check_l3_required BEGIN IMMEDIATE не падает. [HIGH] gate_verify_first auto_verify: event_add без try/except мог уронить task_done. Фикс: try/except (AC5). Тест test_emit_failure_does_not_crash. [HIGH] service_gates/gate_qg0_check: колбкэк scope_hard_gate без guard мог уронить task_start (соседние колбэки guarded). Фикс: try/except вокруг вызова. Тест test_callback_failure_does_not_crash. Ревьюер подтвердил корректными: gate_toggle эмитит только при effective-disable (не при trust-rejection), emit не читает SKIP_HOOKS, все raw INSERT оставляют entry_hash NULL, events_verify зелёный. Full suite: 5205 passed, 0 failed. Урок #268 подтверждён: security-adjacent требует адверс-ревью ДО закрытия.
- 2026-07-21T09:33:18Z [implementation] — AC verified: 1. ✓ _common.emit_supervision_bypass: raw chain-safe INSERT, best-effort try/except, не читает TAUSIK_SKIP_HOOKS. test_bypass_telemetry.py::TestEmitHelper (4 теста: row/no-db/broken-db/no-skip-read) 2. ✓ 6 векторов инструментированы (task_gate/scope_write_gate/bash_firewall/secret_scan/task_done_verify/task_cost_budget_check + git_push_gate + auto_verify + l3_block_downgrade + scope_hard_gate + gates_disable). Hook subprocess end-to-end: TestHookSubprocessWiring (bash_firewall+git_push_gate emit on skip) 3. ✓ supervision_bypasses_summary в backend_queries_metrics + рендер project_cli_metrics (только total>0). test_metric_key_present_and_zero + test_summary_groups_by_action 4. ✓ chain-safe raw INSERT (entry_hash NULL, sealed лениво). test_verify_ok_after_bypass_events: events_verify(seal=True) status=ok 5. ✓ 22 теста в test_bypass_telemetry.py зелёные + full suite 5205 passed 0 failed. Fail-open покрыт: broken-db, event_add-raises (auto_verify), callback-raises (scope_hard_gate) 6. ✓ 3 follow-up заведены: l26-bypass-telemetry-opencode-parity, memory-pretool-block-skip-toggle-and-docstring, hook-fail-open-db-error-telemetry
