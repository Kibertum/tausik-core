---
slug: blocked-is-a-status-without-a-question-to-unblock-it
title: "blocked — статус без вопроса: чем разблокировать задачу, знает только текст журнала"
status: done
epic: release-1-11-3
story: release1113-quality-ratchets
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_migrations_v77.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_postseed.py"
  - "scripts/backend_schema.py"
  - "scripts/project_backend.py"
  - "scripts/service_task.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_errors.py"
  - "scripts/status_view.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "tausik/gates.json"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-tasks.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "tests/test_task_block_question.py"
  - "tests/test_attempts_counter.py"
  - "tests/test_e2e_workflow.py"
  - "tests/test_project_mcp.py"
  - "tests/test_dead_end_gate.py"
  - "tests/test_session_open_handler.py"
  - "tests/test_state_projection_tracks_db.py"
  - "tests/test_actz.py"
  - "tests/test_adapts.py"
  - "tests/test_at.py"
  - "tests/test_reasoning_steps.py"
  - "tests/test_specs.py"
  - "tests/test_session_capacity.py"
  - "tests/test_session_signal_not_gate.py"
  - "tests/test_tausik_service.py"
  - "tests/test_cli_examples_parse.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/**"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T18:37:21Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#93"
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

Заблокированная задача несёт КОНКРЕТНЫЙ вопрос владельцу и критерий разблокировки как поля, а не как прозу в журнале, — и status показывает эти вопросы первым экраном.

## Acceptance Criteria

1. `task block` принимает и ТРЕБУЕТ два поля: question (конкретный вопрос владельцу) и unblock_criteria (что должно стать истиной, чтобы задача пошла дальше). Блокировка без них отвергается — блокировка без вопроса есть задача, брошенная с объяснением для себя.
2. `tausik status` показывает открытые вопросы владельцу ОТДЕЛЬНЫМ блоком в начале, а не строкой «blocked: 1» в общей сводке.
3. `task unblock` проверяет, что критерий разблокировки назван выполненным явно, и записывает КЕМ. Разблокировка молча ЗАПРЕЩЕНА.
4. Живой пример взят как проверка, а не как иллюстрация: release-18-breaking-change-notes висит blocked с 1.8, и чем он разблокируется, сегодня написано прозой в трёх местах. После правки его вопрос и критерий обязаны читаться из полей.
5. НЕГАТИВНЫЙ сценарий: миграция не ломает существующие блокировки — старым записям поля заполняются маркером «не задан», и lint показывает их как долг, а не как норму.
6. НЕГАТИВНЫЙ сценарий: поле question не имеет права выродиться в пересказ заголовка задачи. Гейт отвергает question, совпадающий с title по существу, — иначе поле станет обрядом.

## Plan

## Rollback

git revert коммита; поля остаются в схеме необязательными

## Journal

- 2026-10-07T18:15:08Z [implementation] — HANDOFF STATE (session #299 end). CODE 100%, ALL UNIT LANES GREEN, NOT COMMITTED, NOT CLOSED. INVENTORY (working tree on v1-11-3, 11 commits over 71b313a6): v77 migration (scripts/backend_migrations_v77.py - 4 ALTER + guarded post-step backfill_blocked_questions_v77 with PRAGMA guard, registered in backend_migrations.py + backend_migrations_postseed.py >=77; SCHEMA_VERSION 77 + 4 columns at DDL tail in backend_schema.py; _TASK_FIELDS += 4 in project_backend.py); service_task.py task_block(question, unblock_criteria REQUIRED; token-level guard question-not-title: title tokens subset of question tokens + <=3 added = restatement; re-block UPDATES fields, blocked_at kept) + task_unblock(criterion_met REQUIRED, by defaults user@host, stamps unblocked_by/unblocked_at); status_view.py open_questions in shared data + _open_question_lines rendered FIRST on both channels, marker renders as DEBT with remediation cmd; CLI parser/dispatch/parser_errors example; MCP tools.py schemas + handlers_task.py lambdas; docs EN+RU (cli-tasks block/unblock flags, mcp.md rows + Measured cost 60,273B/60.3KB/15.1k); gates.json: mcp_surface.max_bytes 59602->60273 argued, filesize exempts for service_task.py(599)/project_parser_task.py(510)/project_backend.py(506, ruff re-expands compaction); CHANGELOG EN+RU entry 'Added - a blocked task now carries its question'. TESTS: NEW tests/test_task_block_question.py (12, all 6 ACs incl. migration backfill + DEBT render); updated to new contract: attempts_counter(x2), e2e_workflow, project_mcp, dead_end_gate(x2, one deepened with third assert - dedupe), session_open_handler, state_projection_tracks_db, session_capacity(4; force now TypeError - param deleted), session_signal_not_gate(2), tausik_service(4); fixtures actz/adapts/at/reasoning_steps/specs REVERTED to original (DDL-parity gate forbids hand-declared tasks DDL - hence the post-step move); parser_errors example without [--reason] (examples-parse test). GREEN: 353 passed (migration+parity+fixtures lanes), 113 (4 service lanes), 26 (examples), 12+10+7+18+28... dedupe HELD 282/669, drift exit=0, bootstrap redeploy zero-drift, live DB migrated v76->v77, LIVE CASE DONE: r111-economy-hardening-acceptance re-blocked with real --question/--unblock-when (measurements AC-1..3), live status shows them FIRST. STOPPING POINT: verify #3626 (3.8s) red - 'blocking static gate failed first', pytest did NOT run; the blocking static gate name NOT yet diagnosed. FIRST ACTION next session: Get-Content .tausik/verification/verify-3626.log - find the failing static gate (candidates: test_dedupe growth from the 3 newly-added test files' shapes, class_surface, doc_coverage, scope-narrower). THEN in order: fix -> .tausik/tausik verify --task <slug> (relevant_files already carries 33 paths incl. all touched tests + CHANGELOGs) -> task log AC-evidence AC-1..AC-6 IN CHECKMARK FORM 'AC-N: <what>: <evidence>' with tests/test_... named lines (prior close warned about prose without markers) + Domain line (live status first-screen demonstrates) -> task done --ac-verified --verify-handle via CLI -> commit (message pattern: 'feat(1.11.3): blocked task carries its question - v77 fields, status leads with it'). THEN queue from owner briefing 2026-10-07: Track B #2-5 (nothing-scans-the-installed-harness-state; four-ide-registries-collapse-into-one medium; ratchet-for-mcp-cli-surface-parity complex; agent-friction-becomes-a-filed-defect-not-a-swallowed-one complex); r111-economy-hardening-acceptance MEASUREMENTS ONLY (AC-1 stdio probe vs frozen 63333B per prefix-original-journal-20261002.json, AC-2 frozen replays x3, AC-3 median rounds >=3 natural accepted tasks threshold <=40 baseline 89, AC-5 no synthetics no baseline reconstruction; close on measurements; unblock via new contract with --criterion-met); release 1.11.3 (fill goal on cut-release-1-11-3-version-changelogs-doc, version in scripts/tausik_version.py, [Unreleased]->[1.11.3]+date BOTH changelogs, gen_doc_constants --write + README cells, FULL release verify lane WITH denominators naming deselected, commit, STOP - publication and push ONLY on owner's explicit word IN CHAT, owner said 'ВЛАДЕЛЕЦ ЭТО МЫ' meaning this chat). HARD RULES: gates bite by design never disable; MCP drift -> CLI for verify/task done; bootstrap redeploy after scripts/ edits; dedupe ratchet 282/669; mcp ratchet 149/60273 (bytes move by argued gates.json edit).
- 2026-10-07T18:36:41Z [implementation] — AC-1: ✓ tests/test_task_block_question.py::test_block_without_question_names_both_required_flags и ::test_block_without_criterion_refuses_even_with_a_good_question — блокировка без --question/--unblock-when отвергается; ::test_block_persists_question_and_criteria_and_status_leads_with_them и ::test_reblocking_an_already_blocked_task_updates_the_fields — поля пишутся, переблокировка ОБНОВЛЯЕТ их (blocked_at хранится). AC-2: ✓ status выводит открытые вопросы владельцу отдельным блоком ПЕРВЫМ экраном: tests/test_task_block_question.py::test_block_persists_question_and_criteria_and_status_leads_with_them, ::test_status_renders_a_marker_question_as_debt_not_as_an_answer (status_view.py: open_questions в общих данных, оба канала). AC-3: ✓ tests/test_task_block_question.py::test_unblock_without_a_statement_is_refused_and_quotes_the_criterion — молчаливая разблокировка запрещена, отказ цитирует критерий; ::test_unblock_records_who_stated_the_criterion_met — фиксируется КЕМ (unblocked_by/unblocked_at). AC-4: ✓ живой пример как проверка: r111-economy-hardening-acceptance перезаблокирован с реальными --question/--unblock-when (замеры AC-1..AC-3), поля читаются из БД и выходят первым экраном живого status; исходный кейс release-18-breaking-change-notes закрыт done до посадки этой задачи, его место занял единственный живой blocked. AC-5: ✓ tests/test_task_block_question.py::test_migration_v77_backfills_blocked_rows_with_the_debt_marker — старые blocked-строки получают маркер «не задан»; ::test_status_renders_a_marker_question_as_debt_not_as_an_answer — маркер рендерится как ДОЛГ с командой лечения; живая БД мигрирована v76→v77 (guarded post-step backfill). AC-6: ✓ tests/test_task_block_question.py::test_question_may_not_restate_the_title (parametrized): question-пересказ title отвергается, отличающийся по существу — принимается. Domain: живой .tausik/tausik status (сессия #300, 2026-10-07) первым экраном: «Open question to the owner (1 blocked task): r111-economy-hardening-acceptance — Владелец: принять ли ужесточение экономики 1.11 по естественным замерам…? unblock when: Зафиксированы замеры AC-1..AC-3…» — вопрос и критерий читаются из полей, а не из прозы журнала. Verify: run #3628 PASS (gates 8 passed / 0 failed / 1 skipped hadolint N/A; scoped 248/669 test files: 4678 passed, 18 skipped, 30 deselected), handle 3628.3aed02e5a4afb32116f7470b88ec339b. Красный #3626 разобран и починен: (a) ruff F401 — осиротевший импорт ServiceError в tests/test_session_capacity.py удалён вместе с дублем force-теста (dedupe Group 244: 283/671 → ровно 282/669; единственная копия контракта осталась в tests/test_session_signal_not_gate.py::test_unblock_force_is_refused_too — модульный docstring этого файла владеет стороной retired-flag); (b) tests/test_spec_completeness.py — пин живого замера продлён третьей записью (verification-cohort-contract, UNCHECKED) с аргументацией по решениям #425/#426; это наследство коммитов сессии #299, файл вне relevant_files (receipt фиксирует), уйдёт отдельным коммитом.
- 2026-10-07T18:37:11Z [implementation] — NO-DEAD-END for the rest of the 12 reds: #3616-3625 were the landing itself (filesize cap fought service_task.py at 599 lines - solved by argued gates.json exempt; pytest red until tests carried criterion_met and fixtures reverted per DDL-parity), #3626 was the F401+dedupe pair (dead-end #930), #3627 was live drift: spec-completeness pin still named two UNCHECKED entries after session #299 commits added SPEC verification-cohort-contract - not a failed approach, the pin tracks live state and was extended with the reason.
