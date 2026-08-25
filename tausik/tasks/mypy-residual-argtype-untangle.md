---
slug: mypy-residual-argtype-untangle
title: "Разобрать реальные mypy arg-type/assignment ошибки, снятые per-module disable_error_code в s126"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: mypy-baseline-debt-precommit-hook-lies
scope: "pyproject.toml, scripts/state_import.py, scripts/state_export.py, scripts/gate_post_scope.py, scripts/service_gates.py, scripts/graph_mermaid.py, scripts/service_task.py, scripts/service_knowledge.py"
scope_exclude: "attr-defined оверрайды (Mixin-фасад — отдельная задача), import-not-found/no-any-return/name-defined оверрайды, модули вне списка семи, runtime-поведение (кроме подтверждённого дефекта service_gates, если он есть)"
relevant_files:
  - pyproject.toml
  - "scripts/state_import.py"
  - "scripts/state_export.py"
  - "scripts/gate_post_scope.py"
  - "scripts/gate_run_record.py"
  - "scripts/service_gates.py"
  - "scripts/gate_qg0_check.py"
  - "scripts/graph_mermaid.py"
  - "scripts/service_task.py"
  - "scripts/service_knowledge.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T19:54:56Z"
---

## Goal

mypy-baseline-debt-precommit-hook-lies довёл mypy до 0, но 7 модулей несут per-module disable_error_code для реальных (не config) ошибок типов, отложенных осознанно: state_import (arg-type: node/edge id Any|None→str), state_export (assignment/arg-type: doc-row builders), service_knowledge+service_task (arg-type: auto_export_by_id/auto_export_entity типизированы под ProjectService, зовутся на Mixin — нужна протокол-типизация или cast фасада), gate_post_scope (arg-type: verification_run_id Optional→int), service_gates (arg-type: on_scope_hard_gate_bypass callback возвращает int вместо None — возможно реальный дефект), graph_mermaid (assignment: имя переиспользовано с двумя типами). Задача: убрать каждый disable_error_code, починив тип по-настоящему (протокол/cast/Optional-guard/переименование), по одному коду за раз. Проверка сужена: disable_error_code называет КОНКРЕТНЫЙ код, так что новые ошибки других классов в этих модулях mypy всё ещё ловит.

## Acceptance Criteria

1. Каждый per-module disable_error_code для РЕАЛЬНЫХ type-ошибок убран из pyproject.toml и ошибка починена по-настоящему (Optional-guard / cast-фасад / Protocol / переименование), НЕ подавлена иначе: state_import (arg-type ×3 node/edge id Any|None→str), state_export (assignment+arg-type ×4 doc-row builders), gate_post_scope (arg-type verification_run_id None→int), service_gates (arg-type callback), graph_mermaid (assignment переиспользование имени), service_task (arg-type auto_export_entity), service_knowledge (arg-type auto_export_by_id ×2).
2. service_gates on_scope_hard_gate_bypass callback (Callable[[],int] vs ожидаемый Callable[[],None]|None): решить корректно — либо расширить тип параметра до игнорируемого возврата, либо привести callback к None — с проверкой что fail-open телеметрия-поведение (AC5 из l26-bypass-telemetry) НЕ изменилось.
3. attr-defined оверрайды (project_service/service_task/service_knowledge Mixin-фасад) ОСТАЮТСЯ — это отдельный архитектурный вопрос вне scope; убирается только arg-type в этих модулях.
НЕГАТИВНЫЙ СЦЕНАРИЙ: mypy с временным конфигом БЕЗ соответствующего disable краснел ДО фикса (13 ошибок зафиксированы) и обязан быть зелёным ПОСЛЕ; если фикс неверен (cast скрыл реальный None) — mypy на модуле снова покраснеет либо суита упадёт на этом пути. Проверяется прогоном mypy на всём дереве (Success) + полной суитой.
4. mypy на всём scripts/ = 0 ошибок (Success) с УБРАННЫМИ целевыми disable; полная суита зелёная; scoped verify PASS.

## Plan

[{"step": "Expose all real errors via temp mypy config (13 errors across 7 modules)", "done": true}, {"step": "Fix graph_mermaid (rename), state_export (rename), state_import (isinstance guard)", "done": true}, {"step": "Fix gate_post_scope via record_gate_runs verification_run_id int|None", "done": true}, {"step": "Fix service_gates callback via check_qg0_start param Callable[[],object]|None", "done": true}, {"step": "Fix service_task/service_knowledge via cast('ProjectService', self)", "done": true}, {"step": "Remove target disable_error_code from pyproject; mypy Success on clean cache", "done": true}, {"step": "Full suite green + CHANGELOG + bootstrap sync + verify/close", "done": true}]

## Rollback

git revert коммита — фиксы чисто типовые (guard/cast/rename/аннотации) + удаление строк disable_error_code из pyproject; откат возвращает disable-оверрайды и прежние сигнатуры. Без миграций БД.

## Journal

- 2026-07-26T19:42:07Z [implementation] — Все 13 реальных type-ошибок починены по-настоящему, disable_error_code убраны. graph_mermaid: переименование esrc/etgt (конфликт с tuple|None из nodes.get). state_export: rows→edge_rows (имя занято loop over logs list[dict] на стр.263). state_import: isinstance-guard tgt_type/relation до str (единственное поведенческое изменение — malformed edge FM теперь skip). gate_post_scope: gate_run_record.record_gate_runs verification_run_id int→int|None (колонка nullable FK). service_gates: callback НЕ дефект — check_qg0_start игнорирует возврат (стр.163), расширил param до Callable[[],object]|None. service_task/service_knowledge: cast("ProjectService", self) на facade-границе (Mixin в рантайме = composed ProjectService), attr-defined оверрайд оставлен. Затронуты сверх scope (callee root cause): gate_run_record.py, gate_qg0_check.py. mypy: Success 279 files, 0 ошибок (кэш очищен). Затронутые тесты: 238 passed. Полная суита запущена.
- 2026-07-26T19:53:28Z [implementation] — AC verified: 1. ✓ Все 7 disable_error_code для реальных ошибок убраны из pyproject; фиксы: graph_mermaid rename esrc/etgt, state_export rows→edge_rows, state_import isinstance-guard str, gate_post_scope→record_gate_runs int|None, service_gates→check_qg0_start Callable[[],object]|None, service_task/knowledge cast('ProjectService',self). mypy Success 279 files 2. ✓ service_gates callback вердикт: НЕ дефект — check_qg0_start игнорирует возврат (gate_qg0_check.py:163), fail-open телеметрия не тронута; расширена только аннотация param. Затронутые qg0/scope_hard тесты в suite зелёные 3. ✓ attr-defined оверрайды service_task/service_knowledge/project_service ОСТАВЛЕНЫ (pyproject), убран только arg-type. project_service override не тронут 4. ✓ Domain: mypy на всём scripts/ = Success, 0 ошибок (кэш очищен rm -rf .mypy_cache). Полная суита 6049 passed / 0 failed / 24 skipped — runtime state_import isinstance-guard не сломал экспорт. verify scoped pytest PASS (state_import/export/graph/knowledge). bootstrap --ide all — drift-гейт зелёный
- 2026-07-26T19:54:54Z [implementation] — AC verified: 1. ✓ 7 disable_error_code убраны; фиксы типовые (rename/isinstance/int|None/object-callable/cast). mypy Success 279 files 2. ✓ service_gates callback НЕ дефект (возврат игнорируется gate_qg0_check:163); аннотация расширена. Suite qg0/scope зелёные 3. ✓ attr-defined оверрайды оставлены, убран только arg-type 4. ✓ Domain: mypy Success 0 ошибок; полная суита 6049 passed/0 failed; verify scoped PASS; filesize service_task.py 400<=400; bootstrap drift зелёный
- 2026-07-26T19:55:10Z [done] — Root cause (regression): mypy-baseline-debt довёл до 0 через per-module disable_error_code вместо починки типов — быстрый способ снять gate, оставивший 13 реальных arg-type/assignment ошибок под подавлением по КОНКРЕТНОМУ коду (не blanket). Prevention: disable_error_code — временный откуп с обязательным follow-up defect_of; узкий код (не ignore_errors) держит остальные классы под контролем и делает распутывание по одному коду безопасным. Проверять эффект только после rm -rf .mypy_cache (кэш маскирует override). AC-verify: mypy Success 279 files + полная суита 6049 passed доказывают, что снятие подавления не открыло новых ошибок и не сломало runtime.
