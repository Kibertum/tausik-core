---
slug: med-batch-2-qg
title: "Batch: QG-2 hardening (5 MEDs)"
status: done
epic: v134-hardening
story: qg-hardening
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_negative_scenario.py"
  - "scripts/service_gates.py"
  - "scripts/verify_files_hash.py"
  - "scripts/service_verification.py"
  - "scripts/service_task.py"
  - "scripts/service_task_team.py"
  - "scripts/project_service.py"
  - "scripts/tausik_version.py"
  - "tests/test_senar.py"
  - "tests/test_service_verification.py"
  - "tests/test_session_capacity.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-28T13:57:15Z"
---

## Goal

Bundle: negative-scenario regex (not substring), tier auto-detect uses relevant_files security, files_hash include content sample, task_unblock checks session_capacity, --no-knowledge refused for complex/defect. Closes 5 MED (QG).

## Acceptance Criteria

1. Negative-scenario detection: replace substring with regex requiring boundary phrasing OR distinct AC line; 2. _determine_checklist_tier consults is_security_sensitive(relevant_files) not just title; 3. files_hash includes first 4KiB SHA256 of each file; 4. task_unblock calls check_session_capacity; 5. task_done refuses --no-knowledge if complexity=complex or defect_of non-empty (warning is upgraded to refusal); 6. Tests cover each fix; 7. Negative: 'AC: 1.Works 2.No errors' no longer satisfies negative-scenario requirement.

## Plan

[{"step": "Fix #1 negative-scenario detection: regex requires boundary phrasing (e.g. /\\b(when|if|under)\\s+/i + 'fail|error|reject|invalid') OR distinct AC line", "done": true}, {"step": "Fix #1 \u0442\u0435\u0441\u0442: 'AC: 1.Works 2.No errors' \u0431\u043e\u043b\u044c\u0448\u0435 \u043d\u0435 \u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442; 'AC: ... 5. When token missing, returns clean error' \u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442", "done": true}, {"step": "Fix #2 _determine_checklist_tier: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0432\u0435\u0442\u043a\u0443 if is_security_sensitive(relevant_files): tier=comprehensive", "done": true}, {"step": "Fix #2 \u0442\u0435\u0441\u0442: title='fix typo' + relevant_files=['scripts/auth.py'] \u2192 comprehensive (\u0440\u0430\u043d\u044c\u0448\u0435 standard)", "done": true}, {"step": "Fix #3 files_hash: \u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c SHA256 \u043f\u0435\u0440\u0432\u044b\u0445 4KiB \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0444\u0430\u0439\u043b\u0430 \u0432 \u0445\u0435\u0448 (\u043a\u0440\u043e\u043c\u0435 mtime)", "done": true}, {"step": "Fix #3 \u0442\u0435\u0441\u0442: \u043f\u0440\u0430\u0432\u043a\u0430 content \u043d\u043e mtime \u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d \u2192 hash \u043c\u0435\u043d\u044f\u0435\u0442\u0441\u044f, cache MISS", "done": true}, {"step": "Fix #4 task_unblock: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c check_session_capacity() \u0432 \u043d\u0430\u0447\u0430\u043b\u043e service_task.task_unblock", "done": true}, {"step": "Fix #4 \u0442\u0435\u0441\u0442: session active=181 min \u2192 task_unblock raises CapacityExceededError", "done": true}, {"step": "Fix #5 task_done --no-knowledge: refuse \u0435\u0441\u043b\u0438 complexity=complex \u0438\u043b\u0438 defect_of \u043d\u0435 None, message \u0441 \u044f\u0432\u043d\u044b\u043c reason", "done": true}, {"step": "Fix #5 \u0442\u0435\u0441\u0442: complex task + --no-knowledge \u2192 ServiceError; defect task + --no-knowledge \u2192 ServiceError; simple + --no-knowledge \u2192 \u0432\u0441\u0451 \u0435\u0449\u0451 \u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c qg-related tests \u0437\u0435\u043b\u0451\u043d\u044b\u043c\u0438", "done": true}, {"step": "task done --ac-verified + commit 'fix(qg): negative-scenario regex + tier security check + files_hash content + capacity on unblock + complex/defect knowledge required'", "done": true}]

## Rollback

## Journal

- 2026-04-28T13:56:45Z [implementation] — AC verified: ✓1 has_negative_scenario in gate_negative_scenario.py: regex with word-boundary + negation-redaction filter. Replaced substring `kw in ac_text`. 8 new tests; 'Works without errors' / 'No errors expected' / 'Без ошибок' all correctly fail; 'When token missing returns 401' / 'Ошибка при пустом поле' / 'Returns 500 on backend retry' pass. ✓2 _determine_checklist_tier(task, relevant_files=None) consults is_security_sensitive on relevant_files; 'Fix typo' + scripts/auth.py → 'critical' (was 'lightweight'). 3 new tests. ✓3 compute_files_hash in verify_files_hash.py: now hashes (path, mtime_ns, size, sha256(first_4KiB)). Format version bumped verification_runs.v1 → v2. 3 new tests covering same-mtime/same-size content swap, two distinct files with same mtime, 4KiB bound documentation. ✓4 task_unblock(slug, *, force=False) calls check_session_capacity. 4 new tests covering block-unblock-bypass scenario, force escape hatch, under-capacity success, no-session no-op. ✓5 task_done refuses no_knowledge=True for complex/defect with helpful error. 5 new tests covering simple/medium allow, complex/defect refuse, complex-without-flag pass. ✓6 5/5 fixes covered by tests in test_senar.py + test_service_verification.py + test_session_capacity.py. ✓7 negative-scenario regex test 'AC: 1.Works 2.No errors' (inline numbering) correctly fails — split_ac_into_criteria handles inline numbering. Filesize compliance: extracted gate_negative_scenario.py (101 LOC), verify_files_hash.py (75 LOC), service_task_team.py (62 LOC); all touched modules under 400 (max=385 service_gates). Bootstrap regenerated. CHANGELOG.md + CHANGELOG.ru.md (RU mirror) updated for v1.3.4 with all 4 commits documented. Full pytest: 2332 passed +1 skipped (was 2310). Version bumped 1.3.3 → 1.3.4.
- 2026-04-28T13:57:12Z [implementation] — AC verified: ✓1 has_negative_scenario in gate_negative_scenario.py: regex with word-boundary + negation-redaction filter. Replaced substring `kw in ac_text`. 8 new tests. ✓2 _determine_checklist_tier(task, relevant_files=None) consults is_security_sensitive; 'Fix typo' + scripts/auth.py → 'critical'. 3 new tests. ✓3 compute_files_hash in verify_files_hash.py: now hashes (path, mtime_ns, size, sha256(first_4KiB)). Format bumped v1→v2. 3 new tests. ✓4 task_unblock(slug, *, force=False) calls check_session_capacity. 4 new tests. ✓5 task_done refuses no_knowledge for complex/defect. 5 new tests. ✓6 All 5 fixes covered by tests in test_senar.py + test_service_verification.py + test_session_capacity.py. ✓7 split_ac_into_criteria handles inline 'AC: 1.Works 2.No errors' numbering. Filesize compliance: extracted gate_negative_scenario.py (101 LOC), verify_files_hash.py (75 LOC), service_task_team.py (62 LOC); all touched modules under 400 (max=385). Bootstrap done. CHANGELOG.md + CHANGELOG.ru.md updated for v1.3.4. Full pytest: 2332 passed +1 skipped. Version bumped 1.3.3 → 1.3.4.
