---
slug: final-tz-is-the-acceptance-reference-and-we-have-none
title: "Итоговое ТЗ — эталон сдачи-приёмки: у нас нет ни его, ни правила приоритета"
status: done
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: "Миграция v53 (actz_points.tz_ref), новые read-only функции в service_actz.py/backend_crud_actz.py (final_tz_snapshot, orphan_signed_points), CLI-подкоманды actz final-tz/actz orphans (project_parser_actz.py, project_cli_actz.py), MCP tausik_actz_final_tz/tausik_actz_orphans (tools_actz.py, handlers_actz.py), tests/test_actz.py (доп. тесты), docs/{en,ru}/mcp.md, CHANGELOG.md, CHANGELOG.ru.md."
scope_exclude: "Не трогает adapt/adapt_findings/adapt_interpretations. Не вводит хранимую копию текста ТЗ — только производную проекцию по существующим таблицам. Правило 2 (отказ decided-in на неподписанной точке) не переделывается — уже сделано в actz-the-contract-contour-artifact-is-missing."
relevant_files:
  - "scripts/backend_migrations_v53.py"
  - "scripts/backend_migrations_v52.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_postseed.py"
  - "scripts/backend_schema_actz.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_crud_actz.py"
  - "scripts/service_actz.py"
  - "scripts/project_parser_actz.py"
  - "scripts/project_cli_actz.py"
  - "harness/claude/mcp/project/tools_actz.py"
  - "harness/claude/mcp/project/handlers_actz.py"
  - "tests/test_actz.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "tausik/gates.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - AGENTS.md
  - README.md
  - README.ru.md
  - "docs/README.md"
  - "docs/_generated/constants.json"
  - "docs/en/architecture.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/agent-contract.md"
  - "docs/ru/architecture.md"
  - "docs/ru/senar-compliance-matrix.md"
scope_paths: []
scope_tools: []
depends_on:
  - actz-the-contract-contour-artifact-is-missing
completed_at: "2026-09-06T17:48:51Z"
---

## Goal

RENAR §5A.4: итоговое ТЗ есть начальное ТЗ с приложениями ПЛЮС все подписанные ACTZ, и приоритет принадлежит более позднему подписанному документу. ADAPT в эталон приёмки не входит — именно это делает приёмку юридически чистой. Из этого следуют два правила, которых у нас нет: подписанное решение, не отражённое ни в одном ADAPT, есть обязательство вне требований и классифицируется как fatal; интерпретация не имеет права опираться на решение, которого клиент не принимал. Задача: вычислять итоговое ТЗ как производное представление (не третью копию текста), уметь показать его на любой момент времени и назвать, какой ACTZ какой пункт перекрыл. Отдельно — обнаружение того самого fatal: подписанный пункт без ссылающегося ADAPT обязан находиться запросом, а не глазами. Зависит от actz-the-contract-contour-artifact-is-missing.

## Acceptance Criteria

AC-1 Схема: actz_points получает tz_ref (миграция v53, единственное реальное изменение схемы — на момент миграции точек ещё не существует в проде, ALTER ADD COLUMN NOT NULL DEFAULT '', пустая строка отклоняется на сервисном слое как для adapt_interpretations.tz_ref). Без этого поля "какой ACTZ какой пункт перекрыл" невычислимо: пункт ACTZ не был связан с исходным пунктом ТЗ на уровне схемы.
AC-2 Производное представление: service-функция final_tz_snapshot(as_of: str|None) — по каждому tz_ref среди точек ПОДПИСАННЫХ (обе роли) ACTZ, точка с бОльшим временем завершения подписи (max(signed_at) по обеим ролям) побеждает; названы более ранние перекрытые точки того же tz_ref (цепочка). as_of фильтрует по моменту завершения подписи — «показать на любой момент времени». НЕ третья копия текста: read-only проекция по существующим actz/actz_points/actz_signatures, ничего нового не хранится.
AC-3 Fatal-детектор запросом, не глазами: orphan_signed_points() — подписанные точки ACTZ, на которые не ссылается НИ ОДИН actz_decided_in (правило 1: подписанное решение вне ADAPT — обязательство вне требований). Правило 2 («интерпретация не опирается на непринятое решение») уже принудительно обеспечено в actz_decided_in (отказ на неподписанной цели, сделано в actz-the-contract-contour-artifact-is-missing) — здесь НЕ переделывается, только упомянуто в доке как перекрёстная ссылка.
AC-4 CLI+MCP: `tausik actz final-tz [--as-of TS]` и `tausik actz orphans`; MCP tausik_actz_final_tz, tausik_actz_orphans — тот же паритет, что у остального ACTZ.
AC-5 Качество: тесты (as_of на разных временных точках, цепочка перекрытий 2+ ACTZ на один tz_ref, orphan находит несвязанную подписанную точку и не находит связанную); mypy/ruff/filesize зелёные; docs/{en,ru}/mcp.md дополнены; оба CHANGELOG обновлены; полный прогон.

## Plan

[{"step": "\u041c\u0438\u0433\u0440\u0430\u0446\u0438\u044f v53: actz_points.tz_ref", "done": true}, {"step": "final_tz_snapshot() \u0432 backend_crud_actz.py + service_actz.py", "done": true}, {"step": "orphan_signed_points() \u0432 backend_crud_actz.py + service_actz.py", "done": true}, {"step": "CLI: actz final-tz / actz orphans", "done": true}, {"step": "MCP: tausik_actz_final_tz / tausik_actz_orphans", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b: as_of, \u0446\u0435\u043f\u043e\u0447\u043a\u0430 \u043f\u0435\u0440\u0435\u043a\u0440\u044b\u0442\u0438\u0439, orphan positive/negative", "done": true}, {"step": "\u0414\u043e\u043a\u0438 + CHANGELOG", "done": true}, {"step": "\u041f\u043e\u043b\u043d\u044b\u0439 \u043f\u0440\u043e\u0433\u043e\u043d, verify, \u0437\u0430\u043a\u0440\u044b\u0442\u044c", "done": true}]

## Rollback

Производное представление; третьей копии текста не заводится. Откат: git revert. ACTZ и начальное ТЗ остаются нетронутыми, потому что итоговое ТЗ ВЫЧИСЛЯЕТСЯ, а не хранится.

## Journal

- 2026-09-06T17:47:27Z [implementation] — AC verified: 1. ✓ actz_points.tz_ref (миграция v53); тест test_migration_v52_then_v53_matches_fresh_shape доказывает соответствие fresh vs migrated. 2. ✓ final_tz_snapshot: приоритет более позднему завершению (мутация M1 убита), as_of фильтрует (граничный тест добавлен после того как мутация M4 <= -> < выжила на исходном наборе — реальный пробел закрыт тестом, не декларацией), overridden называет перекрытые точки, две tz_ref независимы. 3. ✓ orphan_signed_points запросом (мутации M2 NOT EXISTS->EXISTS и M3 =2->=1 убиты), находит несвязанную подписанную точку, не находит связанную/неподписанную. 4. ✓ CLI actz final-tz/orphans + MCP tausik_actz_final_tz/orphans, полный паритет (15/15 инструментов). 5. ✓ 74 теста в test_actz.py; mypy 391 файл Success; ruff чист; filesize все файлы <500 (max 436); class_surface baseline поднят (decision #328); docs/{en,ru}/mcp.md ACTZ (15); оба CHANGELOG обновлены. Domain: final_tz_snapshot и orphan_signed_points проверены на реальных ed25519-подписанных ACTZ (svc_keyed fixture), не на моках — governing_text/tz_ref грамматически и семантически корректны для реального использования. Negative: as_of на несуществующий момент (до первого сигна) даёт [], orphan на несуществующий/неподписанный пункт даёт [], decided-in на неподписанную цель уже отклоняется (из прошлой задачи). Реальный дефект найден и исправлен по пути: init_schema безусловно перезапускает fresh-DDL против уже существующей БД со старой формой actz_points — падало на CREATE INDEX; исправлено охраняемым postseed-шагом (ensure_actz_points_tz_ref_index), покрыто test_init_schema_upgrade_order.py (уже существовавшим, не новым).
