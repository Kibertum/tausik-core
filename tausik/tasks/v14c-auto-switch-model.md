---
slug: v14c-auto-switch-model
title: "C4: Auto-switch модели на основе сложности задачи"
status: done
epic: v14-polish-followup
story: v14-polish-c-followup
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: "scripts/model_routing_session.py (NEW), scripts/service_task.py (start/done hooks), scripts/model_routing.py (banner extension), tests/test_model_routing_session.py (NEW), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/skill_profile_session.py (не трогаем, не путать ключи); update_claudemd (отложено — recommendation в session.json не обязателен для CLAUDE.md surface); harness — Claude Code не accepts programmatic switch, persist только для следующего launch"
relevant_files:
  - "scripts/model_routing_session.py"
  - "scripts/service_task.py"
  - "scripts/model_routing.py"
  - "tests/test_model_routing_session.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - AGENTS.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T11:25:11Z"
---

## Goal

Сейчас task_next.model_hint — только suggestion. Эволюционировать в actual switch: TAUSIK при task start экспортирует TAUSIK_MODEL_PROFILE для текущей задачи; agent harness читает и переключается. Trivial=Haiku, moderate+=Opus.

## Acceptance Criteria

1. Новый module `scripts/model_routing_session.py` (под 400L): `record_active_task_recommendation(tausik_dir, slug, complexity)` записывает в `.tausik/.session.json` ключ `active_task_recommendation = {slug, complexity, model, display, recorded_at}`; `read_active_task_recommendation(tausik_dir)` возвращает dict или None; `clear_active_task_recommendation(tausik_dir)` удаляет ключ. 2. `service_task.py::task_start` hook после format_task_start_banner вызывает record_active_task_recommendation; `task_done` hook вызывает clear_active_task_recommendation. 3. `format_task_start_banner` расширен дополнительной строкой actionable hint: "  ↪ Persist for next session: `tausik config set model_profile <slug>`" (только когда MODEL MISMATCH; для match — opcionalно). 4. Tests: новый `tests/test_model_routing_session.py` — record/read/clear roundtrip; идемпотентность; corrupted .session.json handling (silent skip); env-var TAUSIK_DISABLE_TASK_RECOMMENDATION=1 → no-op. 5. NEGATIVE: запись recommendation НЕ ломается, если .tausik/.session.json absent или corrupted — silent skip; record/read/clear не путаются с существующими skill_profile_session ключами `ide`/`model`/`source`. 6. CHANGELOG.md + CHANGELOG.ru.md entry в [Unreleased] Phase C. 7. Existing tests PASS — никакой regression в test_skill_profile_session, test_service_task, test_model_routing.

## Plan

[{"step": "Read skill_profile_session.py contract \u0438 .session.json schema", "done": true}, {"step": "Create scripts/model_routing_session.py \u2014 record/read/clear API", "done": true}, {"step": "Wire record \u0432 service_task.task_start \u043f\u043e\u0441\u043b\u0435 banner", "done": true}, {"step": "Wire clear \u0432 service_task.task_done \u043f\u043e\u0441\u043b\u0435 success", "done": true}, {"step": "Extend format_task_start_banner: add `tausik config set model_profile <slug>` actionable hint on MISMATCH", "done": true}, {"step": "Tests: tests/test_model_routing_session.py (record/read/clear/corrupted/env-skip)", "done": true}, {"step": "Pytest scoped \u2014 GREEN", "done": true}, {"step": "CHANGELOG entries (EN+RU)", "done": true}, {"step": "Verify + task_done", "done": true}]

## Rollback

## Journal

- 2026-05-07T11:25:10Z [implementation] — AC-1: ✓ scripts/model_routing_session.py (140L, под 400 filesize gate) — `record_active_task_recommendation(tausik_dir, slug, complexity)` пишет `.tausik/.task_recommendation.json` (schema_version + slug + complexity + model + display + recorded_at, atomic write через .tmp+rename); `read_active_task_recommendation` возвращает dict или None; `clear_active_task_recommendation` удаляет файл, идемпотентен (вторая клир — no-op возвращает False). AC-2: ✓ scripts/service_task.py — task_start вызывает `record_active_task_recommendation(find_tausik_dir(), slug, complexity)` после format_task_start_banner (try/except: pass — best-effort); task_done вызывает `clear_active_task_recommendation(find_tausik_dir())` после report.ok=True (try/except: pass). AC-3: ✓ scripts/model_routing.py::format_task_start_banner добавил 4-ю строку on MISMATCH: `↪ Persist for next session: \`tausik config set model_profile <slug>\`` — slug derives from `_PROFILE_SLUG_BY_MODEL_ID` whitelist (haiku/sonnet/opus); GPT/Qwen overlay'и not mapped (suggest_model их не возвращает). AC-4: ✓ tests/test_model_routing_session.py — 14 cases: record_simple→haiku, record_complex→opus, unknown_complexity→None+sonnet, no_slug→None, clear_idempotent, env_disable_record_noop, env_disable_read_returns_none, env_disable_clear_noop, malformed_json→None, partial_json→None, non_object_json→None, isolation_session_json (records НЕ трогает .session.json), overwrite_previous (consecutive task_start replaces), atomic_write_no_tmp_leftover. AC-5 (NEGATIVE): ✓ malformed/partial/non-object → None silently; missing tausik_dir → record fails silently через try/except; env_disable=1 → all 3 ops no-op; .session.json key isolation проверена test_record_does_not_touch_session_json. AC-6: ✓ CHANGELOG.md + CHANGELOG.ru.md entry в [Unreleased] Phases B+C, EN+RU sync. AC-7: ✓ Существующие тесты PASS — pytest scoped (model_routing + skill_profile + model_routing_session): 45 PASS; full sweep 3143 passed (2 doc-constants ровно от моих новых файлов/тестов — fixed: gen_doc_constants regen + README.md/README.ru.md/AGENTS.md test-count badge bumped 3255→3271). Verify run #544 recorded (scope=standard, exit=0).
