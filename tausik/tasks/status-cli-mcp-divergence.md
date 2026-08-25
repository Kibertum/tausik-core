---
slug: status-cli-mcp-divergence
title: "CLI и MCP показывают РАЗНЫЙ статус проекта: два презентера одного get_status с непересекающимися наборами сигналов"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/status_view.py (new), scripts/project_cli.py (cmd_status), harness/claude/mcp/project/handlers.py (_handle_status), tests/test_status_view.py, tests/test_project_mcp.py (при необходимости адаптации)"
scope_exclude: "format_status_compact_json (переиспользуется как есть), svc.get_status()/backend_queries, .claude/** и прочие IDE-зеркала (bootstrap-синк), другие MCP-хендлеры, схема БД"
relevant_files:
  - "scripts/status_view.py"
  - "scripts/project_cli.py"
  - "harness/claude/mcp/project/handlers.py"
  - "tests/test_status_view.py"
  - "tests/test_doctor_multi_ide.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T19:30:09Z"
---

## Goal

scripts/project_cli.py:82-170 (cmd_status) и harness/claude/mcp/project/handlers.py:965-1041 (_handle_status) оба форматируют svc.get_status(), но показывают разное: CLI даёт risk-строку, RENAR conformance, epics, calibration drift, session capacity, skill-set warning и НЕ даёт открытую exploration и audit-overdue; MCP — ровно наоборот. Агент на MCP и человек на CLI видят два разных проекта, что подрывает сам смысл общего дашборда. Плюс cmd_status зовёт load_config() ТРИЖДЫ (:87, :126, :156) — три полных резолва трастовых тиров на один вызов — и не передаёт tausik_dir, то есть содержит ровно тот баг (mcp-config-read-paths-ignore-project-handle), который MCP-сторона уже починила и задокументировала у себя. Фикс: status_view.py, возвращающий структурированный dict, плюс по одному рендереру на канал вывода; попутно снимает ~80 строк с 1289-строчного handlers.py.

## Acceptance Criteria

1. Новый scripts/status_view.py: build_status_view(svc, *, verbose, tausik_dir=None) возвращает структурированный dict со ВСЕМИ сигналами (tasks, risk, renar, session-метрики, epics, calibration, capacity, skill-warning, exploration, audit_overdue, duration_warning); load_config вызывается РОВНО ОДИН раз и с tausik_dir.
2. cmd_status (project_cli.py) и _handle_status (handlers.py) оба рендерят из build_status_view; НАБОР сигналов идентичен на обоих каналах — CLI теперь показывает exploration+audit, MCP теперь показывает risk/renar/epics/calibration/capacity. Compact-JSON обоих каналов обогащён одинаково (data['exploration'], data['audit_overdue_sessions']).
3. cmd_status больше НЕ зовёт load_config трижды и передаёт tausik_dir (устраняет mcp-config-read-paths-ignore-project-handle на CLI-стороне, прецедент test_config_read_project_scope).
4. handlers.py уменьшился: inline-логика статуса ушла в status_view.
НЕГАТИВНЫЙ СЦЕНАРИЙ: тест утверждает, что при активной exploration И audit-overdue CLI-рендер (ранее их НЕ показывал) теперь выводит оба, а MCP-рендер при scored-строках/epics выводит risk+epics (ранее НЕ показывал) — рассинхрон закрыт в обе стороны. Существующие MCP compact-контракты (exploration_open/audit_overdue_sessions при пороге; отсутствуют при чистом) сохранены — старые тесты зелёные.
5. Полная суита зелёная; scoped verify PASS.

## Plan

[{"step": "Write scripts/status_view.py: build_status_view (enrich data + gather ALL signals, load_config once w/ tausik_dir) + shared line/warning builders + render_status_cli/render_status_mcp", "done": true}, {"step": "Rewrite cmd_status in project_cli.py to render from build_status_view (single config read, pass tausik_dir)", "done": true}, {"step": "Rewrite _handle_status in handlers.py to render from build_status_view (thin, ~80 lines removed)", "done": true}, {"step": "Add tests/test_status_view.py: divergence-closed negative scenario (CLI shows exploration+audit, MCP shows risk+epics) + config-read-once + compact parity", "done": true}, {"step": "Run existing status tests (test_project_mcp, test_tausik_cli) + scoped verify + full suite", "done": true}, {"step": "Sync mirrors + CHANGELOG", "done": true}]

## Rollback

git revert коммита — новый модуль status_view.py + два тонких рендерера; изменение сигналов аддитивно (каждый канал получает недостающие сигналы), без миграций БД; откат возвращает прежние inline-презентеры cmd_status/_handle_status.

## Journal

- 2026-07-26T19:19:07Z [implementation] — Реализовано: scripts/status_view.py (build_status_view — обогащает data + собирает ВСЕ сигналы, load_config ОДИН раз с tausik_dir, include_rich флаг для compact hot-path; render_status_cli/render_status_mcp из общих status_primary_lines/status_warning_lines). cmd_status и _handle_status переписаны на общий view (handlers.py 1335→1273, −62). Тесты: tests/test_status_view.py (7) — negative divergence в обе стороны, config-read-once scoped, compact-паритет. Все зелёные. Полная суита: 3 падения от рефактора починены: (1) test_doctor_multi_ide claude-literal allowlist — перенёс exemption project_cli.py→status_view.py (skill-warning код переехал); (2) test_check_docs_hook drift — test_count 6195→6213 (18 новых тестов обеих задач), gen_doc_constants --write (README badge авто-синк). Mirror-синк scripts/handlers отложен на bootstrap (иная раскладка .claude/mcp vs harness/, вне scope). Полная суита перезапущена для финального подтверждения.
- 2026-07-26T19:29:11Z [implementation] — AC verified: 1. ✓ scripts/status_view.py::build_status_view — обогащает data + собирает все сигналы; load_config ровно 1 раз с tausik_dir (tests/test_status_view.py::TestConfigReadOnce). include_rich для compact hot-path 2. ✓ cmd_status + _handle_status рендерят из build_status_view. test_status_view.py::TestSignalSetsMatch — CLI теперь показывает exploration+audit, MCP теперь показывает epics; test_both_channels_render_identical_signal_set. Compact обогащён одинаково (TestCompactParity) 3. ✓ cmd_status: единственный load_config(td) через build_status_view, tausik_dir прокинут. TestConfigReadOnce::test_load_config_called_once_and_scoped_to_project (calls[0]==svc.tausik_dir(), count==1) 4. ✓ handlers.py 1335->1273 (-62 строки inline-логики). ruff чист 5. ✓ Domain: полная суита 6049 passed / 0 failed / 24 skipped (real DB/service, не только unit). 3 рефактор-падения (claude-literal allowlist, test_count drift 6195->6213) починены. tausik verify --task standard passed=True [PASS] pytest scoped 5 файлов
- 2026-07-26T19:30:07Z [implementation] — AC verified: 1. ✓ scripts/status_view.py::build_status_view — обогащает data + все сигналы; load_config 1 раз с tausik_dir (TestConfigReadOnce). include_rich для compact 2. ✓ cmd_status + _handle_status рендерят из build_status_view. TestSignalSetsMatch: CLI показывает exploration+audit, MCP показывает epics; test_both_channels_render_identical_signal_set. Compact паритет (TestCompactParity) 3. ✓ cmd_status: единственный scoped load_config(td). TestConfigReadOnce (calls[0]==svc.tausik_dir(), count==1) 4. ✓ handlers.py 1335->1273 (-62). ruff чист. bootstrap --ide all синхронизировал 5 профилей (drift-гейт зелёный) 5. ✓ Domain: полная суита 6049 passed / 0 failed / 24 skipped. verify scoped pytest PASS. test_count 6195->6213 регенерирован
