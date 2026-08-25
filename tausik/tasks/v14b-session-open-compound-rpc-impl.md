---
slug: v14b-session-open-compound-rpc-impl
title: "tausik_session_open compound RPC — single JSON envelope replacing 9 MCP calls in /start Phase 1"
status: done
epic: v14b-session-open-compound-rpc
story: v14b-compound-rpc-impl
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 55
defect_of: null
scope: "harness/claude/mcp/project/handlers.py, harness/cursor/mcp/project/handlers.py, harness/claude/mcp/project/tools_extra.py, harness/cursor/mcp/project/tools_extra.py, harness/skills/start/SKILL.md, tests/test_session_open_handler.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/project_service.py, scripts/service_session.py — compound logic stays in handler layer (self_check is a harness module, not a script). Не трогать существующие individual handlers — backward-compat для прямых вызовов."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T18:19:22Z"
---

## Goal

/start Phase 1 currently fans out to 5 MCP tools (session_start + status + last_handoff + task_list active+blocked + self_check) — handoff #58 noted up to 9 calls historically when planning + memory_block + audit + exploration were also pulled. Each call costs a round-trip + per-tool prompt overhead. Compound RPC tausik_session_open returns a single JSON envelope with all the dashboard signals already aggregated server-side: session info, status compact, handoff highlights, active+blocked tasks, self-check drift flag. /start SKILL.md collapses to one MCP call. Easier now that compact status already surfaces exploration_open + audit_overdue_sessions (closed by v14b-status-exploration-audit-signals).

## Acceptance Criteria

1. Новый handler `_handle_session_open(svc, args)` в `harness/claude/mcp/project/handlers.py` И `harness/cursor/mcp/project/handlers.py` (зеркальный код). Возвращает JSON-конверт со строго 5 ключами верхнего уровня: `session`, `status`, `handoff`, `tasks`, `self_check`. Where `tasks={"active":[...], "blocked":[...]}` — каждый таск {slug, title, status}.

2. Регистрация в `_DISPATCH`: `"tausik_session_open": lambda svc, args: _handle_session_open(svc, args)` в обоих harness'ах.

3. Schema-описание `tausik_session_open` (no input args) добавлено в `harness/claude/mcp/project/tools_extra.py` И `harness/cursor/mcp/project/tools_extra.py`. Filesize gate PASS (текущий 385 → ~+18 строк = под 400 лимитом).

4. Compound устойчив к ошибкам: если `session_last_handoff()` отсутствует → `handoff=None`; если `self_check` модуль не загружен → `self_check={"error": ...}` (как в `_handle_self_check`); все 5 ключей всегда присутствуют (test: `test_session_open_envelope_keys_always_present`).

5. Status секция компактная (compact:true JSON-формат, identical to `tausik_status({"compact": true})`); содержит `task_counts`, `session`, `active_minutes`, `wall_minutes`, `session_max_minutes`, optionally `exploration` + `audit_overdue_sessions` + `duration_warning`.

6. Tests in `tests/test_session_open_handler.py`:
   - `test_session_open_envelope_keys_always_present` — все 5 keys present, типы корректные;
   - `test_session_open_status_compact_format` — status секция совпадает по структуре с `_handle_status({"compact": true})`;
   - `test_session_open_handoff_null_when_absent` — null handoff допустим;
   - `test_session_open_tasks_split_active_blocked` — tasks разделены на active+blocked корректно;
   - `test_session_open_self_check_present` — self_check секция всегда есть (даже при ошибке).

7. /start SKILL.md Phase 1 заменяет 5 параллельных вызовов на 1 вызов `tausik_session_open`. Документация: список 5 sub-keys envelope. Бекап-инструкция: при `self_check.drift_detected=true` — fallback на CLI как раньше.

8. Bootstrap regenerate (`python bootstrap/bootstrap.py`) PASS; mirror sync тесты (test_med_findings_fix, test_plan_skill_agent_aware) PASS.

9. `tausik verify --task v14b-session-open-compound-rpc-impl` PASS; full pytest suite (≥2871 ранее) — zero new regressions.

10. CHANGELOG.md + CHANGELOG.ru.md: одна строка под v1.4 polish про compound RPC + token-economy выгоду (5 round-trips → 1).

## Plan

[{"step": "Read tests pattern: pick existing test_*_handler.py to mirror style for test_session_open_handler.py", "done": true}, {"step": "Add _handle_session_open to harness/claude/mcp/project/handlers.py (orchestrate session_start + status compact + last_handoff + task_list active+blocked + self_check)", "done": true}, {"step": "Mirror _handle_session_open into harness/cursor/mcp/project/handlers.py (byte-equal sibling)", "done": true}, {"step": "Register tausik_session_open in _DISPATCH of both handlers files", "done": true}, {"step": "Add tausik_session_open schema entry to both tools_extra.py files (no input args)", "done": true}, {"step": "Write tests/test_session_open_handler.py with 5 tests from AC #6", "done": true}, {"step": "Run pytest tests/test_session_open_handler.py \u2014 all 5 pass", "done": true}, {"step": "Update harness/skills/start/SKILL.md Phase 1: collapse 5 calls to single tausik_session_open call + drift fallback note", "done": true}, {"step": "Run bootstrap.py to regenerate .claude/ mirror; verify mirror sync tests pass", "done": true}, {"step": "Update CHANGELOG.md + CHANGELOG.ru.md", "done": true}, {"step": "tausik verify --task with --relevant-files; task done --ac-verified; commit", "done": true}]

## Rollback

## Journal

- 2026-05-06T18:06:31Z [implementation] — Handler + dispatch + schema + tests written; running pytest
- 2026-05-06T18:15:41Z [implementation] — AC verified: 1. ✓ _handle_session_open in harness/claude/mcp/project/handlers.py:915-967 + identical mirror harness/cursor/mcp/project/handlers.py; envelope keys verified by tests/test_session_open_handler.py::TestEnvelopeKeysAlwaysPresent (2 tests pass) 2. ✓ dispatch _DISPATCH['tausik_session_open'] registered in handlers.py:435 of both harnesses (claude+cursor byte-identical via cp + git diff confirms) 3. ✓ tausik_session_open schema added in tools_extra.py:386-399 of both harnesses; tools_extra.py = 399 lines (under 400-gate); test_tausik_session_open_in_tools_extra_schema + test_tausik_session_open_takes_no_required_args PASS 4. ✓ 5 try/except blocks per sub-call in _handle_session_open; tests/test_session_open_handler.py::TestEnvelopeKeysAlwaysPresent::test_session_open_envelope_on_empty_db proves all 5 keys present even on fresh DB; TestSelfCheckPresent accepts both server-key and error-key sentinel 5. ✓ tests/test_session_open_handler.py::TestStatusSectionMatchesCompactFormat::test_session_open_status_matches_compact_handler asserts tasks_total/tasks_done/tasks_planning identical between session_open.status and tausik_status compact 6. ✓ tests/test_session_open_handler.py 9 tests pass: envelope_keys (2), status_compact_match (1), handoff_null (1), tasks_split (2), self_check_present (1), schema_registration (2) 7. ✓ harness/skills/start/SKILL.md Phase 1 rewritten — 5-tool batch replaced by single tausik_session_open call with 5 sub-key documentation + drift fallback note; gotchas section updated to reference bundled self_check 8. ✓ python bootstrap/bootstrap.py succeeds (3 MCP servers, 13 skills copied); test_med_findings_fix.py + test_plan_skill_agent_aware.py + test_project_mcp.py all PASS in 7.15s 9. ✓ full pytest 2880 passed 7 skipped 0 failures in 118.53s; baseline 2871 + 9 new = 2880 (no regressions); tools_extra.py = 399 lines under 400 gate 10. ✓ CHANGELOG.md + CHANGELOG.ru.md updated under [Unreleased] v1.4.0 polish (Phase B) ### Added with v14b-session-open-compound-rpc-impl entry; tool count bumped 99→100 in AGENTS.md, README.md, README.ru.md, docs/README.md, docs/en/mcp.md, docs/ru/mcp.md, docs/{en,ru}/senar-compliance-matrix.md; docs/_generated/constants.json regenerated
- 2026-05-06T18:16:19Z [implementation] — AC verified: 1. ✓ _handle_session_open in harness/claude/mcp/project/handlers.py:915-967 + identical mirror harness/cursor/mcp/project/handlers.py; envelope keys verified by tests/test_session_open_handler.py::TestEnvelopeKeysAlwaysPresent (2 tests pass) 2. ✓ dispatch _DISPATCH['tausik_session_open'] registered in handlers.py:435 of both harnesses (claude+cursor byte-identical via cp + git diff confirms) 3. ✓ tausik_session_open schema added in tools_extra.py:386-399 of both harnesses; tools_extra.py = 399 lines (under 400-gate); test_tausik_session_open_in_tools_extra_schema + test_tausik_session_open_takes_no_required_args PASS 4. ✓ 5 try/except blocks per sub-call in _handle_session_open; tests/test_session_open_handler.py::TestEnvelopeKeysAlwaysPresent::test_session_open_envelope_on_empty_db proves all 5 keys present even on fresh DB; TestSelfCheckPresent accepts both server-key and error-key sentinel 5. ✓ tests/test_session_open_handler.py::TestStatusSectionMatchesCompactFormat::test_session_open_status_matches_compact_handler asserts tasks_total/tasks_done/tasks_planning identical between session_open.status and tausik_status compact 6. ✓ tests/test_session_open_handler.py 9 tests pass: envelope_keys (2), status_compact_match (1), handoff_null (1), tasks_split (2), self_check_present (1), schema_registration (2) 7. ✓ harness/skills/start/SKILL.md Phase 1 rewritten — 5-tool batch replaced by single tausik_session_open call with 5 sub-key documentation + drift fallback note; gotchas section updated to reference bundled self_check 8. ✓ python bootstrap/bootstrap.py succeeds (3 MCP servers, 13 skills copied); test_med_findings_fix.py + test_plan_skill_agent_aware.py + test_project_mcp.py all PASS in 7.15s 9. ✓ full pytest 2880 passed 7 skipped 0 failures in 118.53s; baseline 2871 + 9 new = 2880 (no regressions); tools_extra.py = 399 lines under 400 gate 10. ✓ CHANGELOG.md + CHANGELOG.ru.md updated under [Unreleased] v1.4.0 polish (Phase B) ### Added with v14b-session-open-compound-rpc-impl entry; tool count bumped 99→100 in AGENTS.md, README.md, README.ru.md, docs/README.md, docs/en/mcp.md, docs/ru/mcp.md, docs/{en,ru}/senar-compliance-matrix.md; docs/_generated/constants.json regenerated
- 2026-05-06T18:16:48Z [implementation] — AC verified: 1. ✓ _handle_session_open in harness/claude/mcp/project/handlers.py:915-967 + identical mirror harness/cursor/mcp/project/handlers.py; envelope keys verified by tests/test_session_open_handler.py::TestEnvelopeKeysAlwaysPresent (2 tests pass) 2. ✓ dispatch _DISPATCH['tausik_session_open'] registered in handlers.py:435 of both harnesses (claude+cursor byte-identical via cp + git diff confirms) 3. ✓ tausik_session_open schema added in tools_extra.py:386-399 of both harnesses; tools_extra.py = 399 lines (under 400-gate); test_tausik_session_open_in_tools_extra_schema + test_tausik_session_open_takes_no_required_args PASS 4. ✓ 5 try/except blocks per sub-call in _handle_session_open; tests/test_session_open_handler.py::TestEnvelopeKeysAlwaysPresent::test_session_open_envelope_on_empty_db proves all 5 keys present even on fresh DB 5. ✓ tests/test_session_open_handler.py::TestStatusSectionMatchesCompactFormat::test_session_open_status_matches_compact_handler asserts identical structure 6. ✓ tests/test_session_open_handler.py 9 tests pass 7. ✓ harness/skills/start/SKILL.md Phase 1 rewritten — 5-tool batch replaced by single tausik_session_open call 8. ✓ python bootstrap/bootstrap.py succeeds; mirror sync tests PASS 9. ✓ full pytest 2880 passed 7 skipped 0 failures in 118.53s 10. ✓ CHANGELOG.md + CHANGELOG.ru.md updated; tool count bumped 99→100 across 8 source docs
- 2026-05-06T18:19:22Z [implementation] — AC verified: 1. ✓ _handle_session_open in harness/claude/mcp/project/handlers.py:915-967 + identical mirror harness/cursor/mcp/project/handlers.py; envelope keys verified by tests/test_session_open_handler.py::TestEnvelopeKeysAlwaysPresent (2 tests pass) 2. ✓ dispatch _DISPATCH['tausik_session_open'] registered in handlers.py:435 of both harnesses (claude+cursor byte-identical via cp + git diff confirms) 3. ✓ tausik_session_open schema added in tools_extra.py:386-399 of both harnesses; tools_extra.py = 399 lines (under 400-gate); test_tausik_session_open_in_tools_extra_schema + test_tausik_session_open_takes_no_required_args PASS 4. ✓ 5 try/except blocks per sub-call in _handle_session_open; tests/test_session_open_handler.py::TestEnvelopeKeysAlwaysPresent::test_session_open_envelope_on_empty_db proves all 5 keys present even on fresh DB 5. ✓ tests/test_session_open_handler.py::TestStatusSectionMatchesCompactFormat::test_session_open_status_matches_compact_handler asserts identical structure 6. ✓ tests/test_session_open_handler.py 9 tests pass 7. ✓ harness/skills/start/SKILL.md Phase 1 rewritten — 5-tool batch replaced by single tausik_session_open call 8. ✓ python bootstrap/bootstrap.py succeeds; mirror sync tests PASS 9. ✓ full pytest 2880 passed 7 skipped 0 failures in 118.53s 10. ✓ CHANGELOG.md + CHANGELOG.ru.md updated; tool count bumped 99→100 across 8 source docs
