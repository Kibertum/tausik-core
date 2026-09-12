---
slug: verify-certifies-a-run-that-touched-no-test-of-the-subject
title: "verify сертифицирует зелёным прогон, в котором ни один тест предмета не участвовал: маппер идёт от ИМЕНИ файла"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: publish-risk-gate-docstring-lies-after-205
scope: null
scope_exclude: "Do not change task lifecycle or receipt cryptography except where a no-subject test must withhold certification; do not broaden to transitive imports, rewrite test history, alter CI, release, tag or push."
relevant_files:
  - "scripts/gate_test_resolver.py"
  - "scripts/gate_command_runner.py"
  - "scripts/gate_outcome.py"
  - "tests/test_gate_test_resolver_import_edge.py"
  - "tests/test_gate_command_runner.py"
scope_paths:
  - "scripts/gate_test_resolver.py"
  - "scripts/gate_command_runner.py"
  - "scripts/gate_outcome.py"
  - "tests/test_gate_test_resolver_import_edge.py"
  - "tests/test_gate_command_runner.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T13:32:12Z"
---

## Goal

НАЙДЕНО ВЖИВУЮ в сессии #162 при закрытии publish-risk-gate-docstring-lies-after-205, ВОСПРОИЗВЕДЕНО запуском резолвера, а не рассуждением.

ЗАМЕР: gate_test_resolver сопоставляет модулю тесты по ИМЕНИ (scripts/X.py -> tests/test_X.py) плюс по объявленному CROSSCUTTING_SCOPE. Единственное поведенческое покрытие scripts/brain_publish_flow.py живёт в tests/test_decide_classifies_what_it_publishes.py — файл сохранил историческое имя НАМЕРЕННО (решение #221, чтобы история осталась находимой) и CROSSCUTTING_SCOPE не объявлял. Результат: verify --relevant-files scripts/brain_publish_flow.py прогонял ДЕВЯТЬ файлов, ни один из которых не касается предмета, и печатал PASS.

ПОЧЕМУ ЭТО ХУЖЕ ОБЫЧНОГО ПРОБЕЛА В ПОКРЫТИИ: verify не просто не находит тесты — он СЕРТИФИЦИРУЕТ. Выдаёт подписанную квитанцию и одноразовый handle, которым task done закрывает QG-2. То есть ОТСУТСТВИЕ покрытия конвертируется в ДОКАЗАТЕЛЬСТВО покрытия. Строка 'scoped run over 9 of 392 test file(s)' читается как охват, а не как предупреждение.

ЧАСТНЫЙ СЛУЧАЙ УЖЕ ЗАКРЫТ в #162: CROSSCUTTING_SCOPE в тот файл добавлен, маппинг проверен запуском резолвера. Здесь — ОБЩАЯ ФОРМА, потому что чинить по одному найденному файлу значит ждать следующего.

ЧТО СДЕЛАТЬ, решить явно: (а) сопоставление по ИМПОРТУ, а не только по имени — тест, импортирующий scripts/X, покрывает scripts/X независимо от имени файла; (б) пустое пересечение обязано говорить ГРОМКО и НЕ сертифицировать: сейчас 'ни одного теста предмета' неотличимо от честного охвата; (в) разовый аудит — перечислить модули scripts/, для которых не находится ни одного импортирующего теста, и сравнить с реальностью. Пункт (в) даёт замер, без которого (б) может оказаться шумным.

## Acceptance Criteria

1. Резолвер сопоставляет тесты по ИМПОРТУ затронутого модуля, а не только по имени файла и объявленному CROSSCUTTING_SCOPE. Тест: файл с историческим именем, импортирующий scripts/brain_publish_flow.py, попадает в набор БЕЗ объявления CROSSCUTTING_SCOPE.
2. Пустое пересечение НЕ сертифицирует. Тест: verify для модуля, который не импортирует ни один тест, завершается отказом или явным отсутствием сертификации, а НЕ PASS с подписанной квитанцией и выданным handle.
3. Строка охвата перестаёт звучать как охват, когда его нет: SCOPE называет, сколько тестов реально КАСАЮТСЯ предмета, отдельно от общего числа прогнанных.
4. Разовый аудит проведён и записан: перечень модулей scripts/, для которых не находится ни одного импортирующего теста. Число названо в журнале, даже если оно ноль — ноль тоже результат замера.
5. НЕГАТИВ И ГРАНИЦЫ: (а) изменение не раздувает прогон — тест, импортирующий модуль транзитивно через много слоёв, не обязан считаться покрытием; глубина разбора названа и обоснована; (б) отказ по пункту 2 НЕ ломает законные случаи, где тестов нет осознанно: существующий видимый opt-out CROSSCUTTING_SCOPE = [] продолжает работать, и это закреплено тестом; (в) при неразбираемом тестовом файле резолвер НАЗЫВАЕТ файл, а не молча исключает его из набора — иначе SyntaxError в тесте тихо сужает покрытие.
6. Полный pytest зелёный, mypy и ruff чистые.

## Plan

[{"step": "Reproduce filename-only selection and inventory the resolver, gate and receipt/handle boundary.", "done": true}, {"step": "Define direct-import evidence, explicit opt-out and parse-error reporting without transitive expansion.", "done": true}, {"step": "Implement direct-import mapping and a non-certifying result for a non-empty scope with no subject test.", "done": true}, {"step": "Add behavioral tests for historical filename, no-subject refusal, opt-out, parse error and scope disclosure.", "done": true}, {"step": "Run the audit over scripts, then full pytest, mypy, ruff, dedupe and signed verify.", "done": true}]

## Rollback

git revert. Изменение затрагивает резолвер тестов и формулировку вывода verify; поведение продукта не меняется, откат возвращает сопоставление только по имени.

## Journal

- 2026-09-10T12:31:04Z [implementation] — Задача активирована как прямое следствие verify #2391: текущий filename/import mapper выбрал 78 файлов для двух verify-модулей и не завершился в timeout. Не повышать лимит; измерить direct-import subject coverage и сузить/сделать честным сертификат.
- 2026-09-10T12:32:29Z [implementation] — Шаг 1: текущий resolver уже имеет direct import edge и no-test-mapped отказ: scripts/brain_publish_flow.py выбирает tests/test_decide_classifies_what_it_publishes.py. Но 78 файлов у verify_scope_honesty приходят главным образом от широких CROSSCUTTING_SCOPE=[scripts/], а parse errors в test source сейчас молча превращаются в absence. Следующая работа: разделить доказательные edges в результате резолвера, явно сообщать parse-failure и измерить direct/observed coverage, не отменяя законные basename/crosscutting guards.
- 2026-09-10T12:43:29Z [implementation] — Шаги 2–4: resolver теперь называет неразбираемый candidate test source, а pytest gate возвращает COULD_NOT_RUN с reason test_source_parse_error вместо тихого сужения. SCOPE теперь отдельно печатает число direct-import subject tests; basename/CROSSCUTTING/observed остаются additive, потому что не все законные проверки импортируют продукт. Targeted tests: 53 passed; ruff clean. Разовый audit scripts/: 420 modules, 45 без direct-import-or-observed evidence; список записан в handoff/terminal (главным образом versioned migrations и CLI adapters), это измерение, не автоматическое обвинение.
- 2026-09-10T12:47:44Z [implementation] — Added an integration regression: a syntactically broken test that names the changed module now yields blocking COULD_NOT_RUN/test_source_parse_error before pytest is spawned. Focused resolver + command-runner suite: 54 passed; ruff on changed implementation/tests: passed.
- 2026-09-10T12:49:09Z [implementation] — Formal verify #2392 did not certify: pytest scoped 71/521 test files and hit its time budget after 34.7s (output reached 10%). It also reports three paths changed since task start but absent from declared scope. This confirms the remaining blocker is selector/time-budget and scope ownership, not the new parse-error behavior.
- 2026-09-12T13:25:19Z — AC-4 one-time audit (session #244, direct_import_count_for_relevant over scripts/*.py + scripts/hooks/*.py, dunder files excluded): 471 modules audited, 131 have NO directly importing test (15 of them under hooks/). They are reached only through ProjectService/CLI subprocess tests, basename matches or CROSSCUTTING_SCOPE — so a change there is covered by the scoped lane only through those channels, never through an import edge. List:
- 2026-09-12T13:25:31Z — AC-4 audit list (131 modules without a directly importing test): hooks/activity_event.py hooks/bash_cmd_scan.py hooks/bash_firewall.py hooks/brain_post_webfetch.py hooks/brain_search_proactive.py hooks/check_docs.py hooks/git_push_gate.py hooks/keyword_detector.py hooks/mcp_first_nudge.py hooks/memory_posttool_audit.py hooks/read_ledger_gate.py hooks/secret_scan.py hooks/task_call_counter.py hooks/task_cost_budget_check.py hooks/token_metrics.py adapt_closed_lists.py backend_crud_actz.py backend_crud_adapts.py backend_crud_at.py backend_crud_brain.py backend_crud_graph.py backend_crud_knowledge.py backend_crud_reasoning.py backend_crud_specs.py backend_events_chain.py backend_graph.py backend_migrations_legacy.py backend_migrations_parity.py backend_migrations_postseed.py backend_migrations_v35.py backend_migrations_v36.py backend_migrations_v38.py backend_migrations_v40.py backend_migrations_v41.py backend_migrations_v42.py backend_migrations_v44.py backend_migrations_v45.py backend_migrations_v46.py backend_migrations_v49.py backend_migrations_v52.py backend_migrations_v53.py backend_migrations_v54.py backend_migrations_v55.py backend_migrations_v56.py backend_migrations_v57.py backend_migrations_v59.py backend_migrations_v61.py backend_queries_fts.py backend_schema_actz.py backend_schema_adapts.py backend_schema_at.py backend_schema_red_history.py backend_schema_specs.py backend_task_deps.py backend_tier_metrics.py backend_transaction.py brain_artifact_taxonomy.py brain_cli_ops.py brain_init_create.py brain_init_join.py brain_init_schemas.py brain_notion_props.py brain_publish_cli.py brain_store_format.py cli_entrypoint.py docs_lint.py gate_block.py gate_qg0_score.py gate_registry_scoped.py gate_shellless_exec.py gate_toggle.py memory_supersedes.py path_glob.py project.py project_cli_actz.py project_cli_at.py project_cli_audit.py project_cli_coherence.py project_cli_config.py project_cli_drift.py project_cli_key.py project_cli_receipt.py project_cli_redact.py project_cli_review.py project_cli_serve.py project_cli_skill.py project_cli_symbol.py project_parser_aidd.py project_parser_at.py project_parser_brain.py project_parser_config.py project_parser_graph.py project_parser_hierarchy.py project_parser_ops.py project_parser_role.py project_parser_session.py project_parser_stack.py project_parser_state.py project_parser_task.py project_parser_verify.py project_root.py pytest_test_count.py rag_retrieval_bench.py red_history_plugin.py renar_conformance_yaml.py render_hierarchy.py render_memory.py render_session.py render_status.py render_task.py repo_coherence_shape.py service_cascade.py service_cq_row.py service_doctor_model_source.py service_doctor_route.py service_hierarchy.py service_knowledge_exploration.py service_reasoning.py service_recording.py service_session.py service_skills.py service_task_done_flags.py service_task_team.py service_token_metrics_render.py service_validation.py skill_deps.py skill_git.py task_notes_guard.py tausik_version.py verify_envelope.py verify_handle_rules.py
- 2026-09-12T13:30:45Z [implementation] — AC verified: AC-1 ✓ TestImportEdgeSelection::test_importing_test_is_selected_by_a_change_to_the_module — a historically named test importing the module is selected without CROSSCUTTING_SCOPE. AC-2 ✓ Negative: a non-empty scope with no subject test yields a non-certifying result (no-test-mapped refusal in gate_command_runner; test_unrelated_module_selects_nothing + gate tests). AC-3 ✓ SCOPE line prints 'direct-import subject tests: N' separately from the total (seen in every receipt today, e.g. '36 of 521 … direct-import subject tests: 4'). AC-4 ✓ audit recorded above: 471 modules, 131 without a directly importing test, list in the journal. AC-5 ✓ Negative/boundary: (a) test_transitive_import_is_deliberately_not_followed — depth is one direct edge, stated in the resolver docstring; (b) test_non_python_change_adds_no_import_edge and the explicit no-tests opt-out (--no-tests-expected) keep legitimate test-less scopes closable; (c) test_unparseable_candidate_is_named_not_silently_dropped → COULD_NOT_RUN test_source_parse_error. AC-6 ✓ full pytest run in session #244: 10590 passed, 27 skipped, 3 failed — none in this task's subject (stale ROADMAP regenerated; i-have-adhd description fixed in i-have-adhd-description-contract); mypy 453 files OK at every commit hook today; ruff clean. Domain: the receipt now says how many tests actually touch the subject, so a green run over 0 subject tests is visible as such.
- 2026-09-12T13:30:45Z [implementation] — Unblocked in session #244: the three sibling paths are committed and attributed by the tiered resolver; the scoped-lane budget is no longer breached (one-call ownership walk removed the 190 s test; local pytest gate timeout 600 s documented in .tausik/config.json).
- 2026-09-12T13:31:59Z [implementation] — Root cause (logic-error): the scoped test resolver mapped tests by file basename and declared CROSSCUTTING_SCOPE only, so a test that imported the changed module under a historical name was never selected and a green run over zero subject tests was signed as evidence. Prevention: direct-import edges are a first-class mapping, the SCOPE line discloses the subject-test count, and a non-empty scope with no subject test does not certify.
