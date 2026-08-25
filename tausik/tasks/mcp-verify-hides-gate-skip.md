---
slug: mcp-verify-hides-gate-skip
title: "MCP tausik_verify отдаёт только имена гейтов — SKIP неотличим от PASS, а CLAUDE.md предписывает MCP-first"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "harness/claude/mcp/project/handlers.py (_handle_verify), tests/ (тест на формат ответа), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/service_gates.py и scripts/gate_runner.py (вердикты там уже есть и корректны — теряются только в сериализации MCP), CLI-форматтер project_cli_verify.py (он и есть эталон)"
relevant_files:
  - "harness/claude/mcp/project/handlers.py"
  - "tests/test_mcp_verify_handler.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-24T08:41:10Z"
---

## Goal

Найдено в сессии #133 при закрытии bash-firewall-lacks-command-normalization. harness/claude/mcp/project/handlers.py::_handle_verify строит ответ как gates=[r.get("name") for r in results] — то есть выбрасывает per-gate поля passed и skipped. Агент видит `verify passed=True gates=['hadolint','pytest']` и читает это как «pytest прошёл», тогда как фактически pytest был SKIPPED (пустой relevant_files → нет маппинга test_<basename>.py), а PASS дал только hadolint, линтер Dockerfile, к python-правке отношения не имеющий. CLI печатает `[SKIP] pytest` и различие видно; MCP — нет. При этом CLAUDE.md прямо предписывает MCP-first, то есть штатный путь агента — тот, который сигнал теряет. Прогон при этом записывается в verification_runs с exit=0 и ПОДПИСЫВАЕТСЯ receipt'ом, а task done --ac-verified принимает такой кэш: цепочка «зелёный verify → закрытие» может держаться на прогоне, где ни один релевантный гейт не исполнялся. Это ровно тот класс тихой лжи, против которого построен gate_verdict (см. _NO_IMPL_SENTINEL в gate_runner.py: «a gate that never executes reporting success — the exact reading gate_verdict exists to forbid»).

## Acceptance Criteria

1. Воспроизведение зафиксировано ДО правки: MCP tausik_verify на задаче без relevant_files возвращает строку, где pytest неотличим от исполненного, тогда как CLI на том же прогоне печатает [SKIP]. Сравнение обеих строк записано в журнал.
2. Ответ MCP несёт ВЕРДИКТ каждого гейта, а не имя: как минимум PASS/FAIL/SKIP на гейт. Формат сверен с CLI — агент, читающий MCP, должен получать тот же вывод о том, что исполнилось, что и агент, читающий CLI.
3. Пустая область больше не выглядит как верификация: когда relevant_files пуст ИЛИ все scoped-гейты пропущены, ответ MCP говорит это ЯВНО и называет исполнимое действие (объявить relevant_files), а не только имена гейтов.
4. Тест: прогон verify без relevant_files и с ними даёт РАЗЛИЧИМЫЕ ответы MCP-хендлера; тест падает на прежнем формате.
5. Проверено, что паритет CLI↔MCP не сломан в обратную сторону: существующие тесты MCP-хендлеров и verify-first контракта зелёные.
6. Правка идёт в ИСТОЧНИК harness/claude/mcp/project/handlers.py, затем bootstrap --ide all; bootstrap_drift зелёный.

## Plan

## Rollback

git revert + bootstrap --ide all. Правка чисто презентационная (сериализация ответа), поведение гейтов не меняется, поэтому откат не может открыть дыру — он лишь вернёт потерю сигнала.

## Journal

- 2026-07-24T08:41:08Z [implementation] — AC-1: ✓ воспроизведено ДО правки на одной и той же задаче (firewall-rm-wipe-targets-policy, у неё нет relevant_files). MCP вернул: verify passed=True status=miss trigger=verify gates=['hadolint','pytest']. CLI на том же прогоне: [PASS] hadolint / [SKIP] pytest / Duration: 0 ms. Прогон записан как #1253 и ПОДПИСАН — то есть подписанный зелёный чек существует для прогона, где не исполнилось ничего релевантного. AC-2: ✓ хендлер переведён на gate_runner.format_results — тот же форматтер, что у CLI, вердикт PASS/FAIL/SKIP на каждый гейт. AC-3: ✓ добавлены две NOTE — перечисление НЕ исполнившихся гейтов и, при пустой области, конкретная команда tausik task update --relevant-files. AC-4: ✓ tested via tests/test_mcp_verify_handler.py::TestMcpVerifyReportsGateVerdicts (5 тестов). Падение на ПРЕЖНЕМ формате проверено прогоном, а не заявлено: файл возвращён через git checkout, прогон дал 4 failed / 7 passed, затем восстановлен (git diff подтверждает +34/-5). Пятый тест (test_all_passed_run_carries_no_skip_note) зелёный на обеих версиях намеренно — он держит границу в обратную сторону, чтобы фикс не начал клеить пометку о пропуске к честно зелёным прогонам. AC-5: ✓ паритет не сломан: tests/test_mcp_verify_handler.py + test_mcp_integration.py + test_verify_first_contract.py + test_project_mcp.py = 74 passed. AC-6: ✓ правка в источнике harness/claude/mcp/project/handlers.py, выполнен bootstrap --ide all, bootstrap_drift зелёный. Дополнительно: проверено, что других мест с рендером гейтов по именам не осталось (grep по MCP-дереву и scripts/) — этот хендлер был последним, шестым к пяти, найденным задачей verify-summary-reports-skipped-as-pass. Domain: результат осмыслен вне тестов — расхождение двух поверхностей на ОДНОМ прогоне и есть предметное доказательство; после правки обе печатают один и тот же вердиктный список. Замечание для аудита: verify зафиксировал 2 недекларированных изменённых файла — это незакоммиченные правки предыдущих задач сессии, чек честно записал более узкое покрытие.
