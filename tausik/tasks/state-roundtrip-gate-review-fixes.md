---
slug: state-roundtrip-gate-review-fixes
title: "Фиксы адверсариального ревью state_roundtrip гейта: fail-open дыра импорта + staged-vs-worktree"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: state-git-roundtrip-gate
scope: "scripts/gate_state_roundtrip.py, scripts/state_import.py, scripts/status_view.py, scripts/doc_drift_common.py, tests/test_state_roundtrip_gate.py, tests/test_state_import*.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "gate_registry регистрация (не меняется), state_export/state_serialize, другие гейты, 2000 экспортированных файлов"
relevant_files:
  - "scripts/gate_state_roundtrip.py"
  - "scripts/state_triggers.py"
  - "scripts/state_import.py"
  - "scripts/project_cli_state.py"
  - "scripts/status_view.py"
  - "tests/test_state_roundtrip_gate.py"
  - "tests/test_state_import.py"
  - "tests/test_state_triggers.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T21:31:48Z"
---

## Goal

Адверсариальное ревью волны нашло 2 HIGH в новом gate_state_roundtrip.py + сопутствующие MED/LOW. HIGH-1: `from state_export import ExportError` вне try/except — ImportError сломает gate_runner (impl() вызывается без обёртки, gate_runner.py:151), нарушая собственный инвариант fail-open. HIGH-2: гейт сверяет РАБОЧЕЕ ДЕРЕВО с БД, а commit-flow стейджит КОНКРЕТНЫЕ файлы (skill: 'prefer specific files', не git add -A) — 'забыл git add tausik/' даёт ложный зелёный (коммит без экспорта). MED: нет теста ExportError→block; state_import isinstance-guard молча роняет malformed рёбра (нет в import-report); гейт block без transition-ноты для дрейфующих проектов. LOW: status_view audit except уже широкого не как остальные; комментарий про allow-list квалификатора.

## Acceptance Criteria

1. HIGH-1: `from state_export import ExportError` перенесён внутрь try/except гейта — ImportError даёт fail-open '(unavailable)', НЕ пробрасывается в gate_runner. Тест: импорт ломается → гейт (True, unavailable), не raise.
2. HIGH-2: гейт после worktree==БД дополнительно проверяет, что managed-пути под tausik/ ПОЛНОСТЬЮ застейджены (git porcelain: нет working-tree-dirty/untracked под tausik/); иначе red 'stage tausik/'. Тест: worktree==БД но файл не застейжен → red. Fail-open если git недоступен.
3. MED: тест ExportError→block; state_import при отбросе malformed ребра пишет в report['skipped_edges'] (виден в выводе). LOW: status_view audit_overdue except расширен до Exception. CHANGELOG upgrade-нота (export перед первым коммитом).
НЕГАТИВ: (а) сломанный импорт → fail-open, gate_runner НЕ падает; (б) экспортирован но не застейжен → red (ловит забытый git add); (в) malformed ребро → в report, не молча.
4. Полная суита зелёная; mypy Success; scoped verify PASS.

## Plan

[{"step": "HIGH-1: move ExportError import inside try (fail-open survives import failure)", "done": true}, {"step": "HIGH-2: staged-check via git porcelain after worktree==DB match", "done": true}, {"step": "MED-3: test ExportError->block + fail-open-internal-fault", "done": true}, {"step": "MED-4: state_import surface skipped_edges in report + CLI; found+fixed _tree_root ambient-cwd bug (svc-scoped)", "done": true}, {"step": "LOW: status_view widen except; CHANGELOG upgrade note", "done": true}, {"step": "Fix subprocess convention (encoding+stdin) violations flagged by suite", "done": true}, {"step": "Full suite green + mypy + bootstrap + close", "done": true}]

## Rollback

git revert (когда закоммичено) — правки локализованы в gate_state_roundtrip.py (import + staged-check), state_import.py (report-строка), status_view.py (широкий except); откат возвращает прежние версии. Без миграций БД, гейт остаётся зарегистрированным.

## Journal

- 2026-07-26T21:20:44Z [implementation] — Все находки ревью разобраны. HIGH-1: `from state_export import ExportError` внутрь try + вложенный try для build_tree — ImportError теперь fail-open, не крашит gate_runner. HIGH-2: _unstaged_managed_paths (git status --porcelain -- tausik) после worktree==БД; untracked/worktree-dirty → red 'git add tausik/'; fail-open если git недоступен. MED-3: test_export_error_is_a_hard_block + test_internal_fault_fails_open. MED-4: state_import пишет skipped_edges в report + CLI выводит; ПОПУТНО найден+починен смежный дефект — state_triggers._tree_root брал ambient find_tausik_dir (cwd) вместо svc.tausik_dir → auto_export писал в ЧУЖОЙ (реальный) tausik/ при тестах на tmp-БД; теперь _tree_root(svc) svc-scoped; реальное дерево вычищено ре-экспортом. LOW: status_view audit except→Exception; CHANGELOG upgrade-нота EN+RU. Суита выявила 2 конвенции нарушенными в новом subprocess (гейт + git-тест): добавлены encoding='utf-8'+stdin=DEVNULL. mypy Success, ruff чист, bootstrap синхронизирован. Тесты: 17 ранее-падавших зелёные. Финальная суита запущена.
- 2026-07-26T21:31:18Z [implementation] — AC verified: 1. ✓ HIGH-1: ExportError импорт внутри try + вложенный try; test_state_roundtrip_gate.py::TestFailOpenAndExportError::test_internal_fault_fails_open_never_raises (broken build_tree → (True, unavailable), не raise) 2. ✓ HIGH-2: _unstaged_managed_paths (git porcelain, stdin=DEVNULL, encoding=utf-8); TestStagedCheck::test_red_when_export_unstaged (worktree==БД но не застейжено → red 'git add tausik/'), test_green_when_export_staged, test_red_when_staged_then_worktree_edited 3. ✓ MED-3: test_export_error_is_a_hard_block. MED-4: state_import skipped_edges в report+CLI, test_malformed_edge_is_reported_not_silently_dropped (via _apply_edges direct). Смежный дефект _tree_root ambient→svc-scoped, test_state_triggers зелёные, реальное дерево вычищено. LOW: status_view except→Exception; CHANGELOG upgrade-нота EN+RU 4. ✓ Domain: полная суита 6063 passed / 0 failed / 24 skipped (real DB/git subprocess). mypy Success. verify scoped pytest PASS (4 файла). bootstrap drift зелёный. subprocess конвенции (encoding+stdin) выправлены под гейты test_hook_encoding/test_risk_compute_stdin
- 2026-07-26T21:31:36Z [implementation] — Root cause (logic-error): новый gate_state_roundtrip.py имел два дефекта, найденных адверсариальным ревью. (1) `from state_export import ExportError` стоял ВНЕ try-блока fail-open — импорт-сбой пробился бы в gate_runner (impl() зовётся без обёртки) и уронил бы весь commit-gate прогон, нарушив собственный инвариант гейта. (2) гейт сверял РАБОЧЕЕ ДЕРЕВО с БД, а commit стейджит конкретные файлы — 'забыл git add tausik/' давал ложный зелёный. Смежно: state_triggers._tree_root брал ambient cwd (тот же класс, что mcp-config-read-paths-ignore-project-handle). Prevention: (а) в fail-open гейте ВСЕ импорты и работа — внутри try; ExportError различать вложенным try; (б) гейт над тем-что-войдёт-в-git обязан смотреть ИНДЕКС/staged, не рабочее дерево; (в) резолвинг путей проекции — от svc, не от cwd; (г) subprocess в scripts/ всегда stdin=DEVNULL + encoding='utf-8' (гейты test_risk_compute_stdin/test_hook_encoding это ловят). Адверсариальное ревью новых гейтов обязательно — сам гейт защищает коммиты, его дыра тиха.
- 2026-07-26T21:31:46Z [implementation] — AC verified: 1. ✓ HIGH-1 fail-open: test_internal_fault_fails_open_never_raises 2. ✓ HIGH-2 staged-check: TestStagedCheck (unstaged→red, staged→green, worktree-edit→red) 3. ✓ MED-3 ExportError→block; MED-4 skipped_edges (report+CLI) + _tree_root svc-scoped fix; LOW status_view except + CHANGELOG нота 4. ✓ Domain: суита 6063 passed/0 failed; mypy Success; verify PASS; subprocess encoding+stdin конвенции выправлены
