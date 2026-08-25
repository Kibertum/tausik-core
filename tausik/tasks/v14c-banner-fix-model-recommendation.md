---
slug: v14c-banner-fix-model-recommendation
title: "C7: Fix model recommendation banner — drop incorrect /fast advice"
status: done
epic: v14-polish-followup
story: v14-polish-c-followup
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "scripts/model_routing.py, bootstrap/bootstrap_templates.py, QWEN.md, tests/test_task_start_model_banner.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "docs/, README.md, README.ru.md, CHANGELOG entries для прошлых версий (исторические записи не трогаем)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T16:51:17Z"
---

## Goal

Текущий баннер `task_start` при model mismatch говорит "↪ switch to Sonnet 4.6 via /fast" — НЕВЕРНО. Per system prompt: "/fast uses Claude Opus 4.6 with faster output (does NOT downgrade to a smaller model)". Заменить на корректный текст: drop /fast, оставить только `tausik config set model_profile <slug>` (next-session persist) + явное уведомление "manual switch only via IDE model picker — Claude Code does not expose programmatic mid-session switch".

## Acceptance Criteria

AC1: Banner на MISMATCH больше не содержит "/fast" — заменено на явный hint про IDE model picker и отсутствие programmatic switch.
AC2: Persist hint `tausik config set model_profile <slug>` показывается ВСЕГДА на MISMATCH для 3 routed моделей.
AC3: Module docstring scripts/model_routing.py (lines 3-5) — убран "/fast" reference.
AC4: bootstrap/bootstrap_templates.py:46 — "/fast" заменён на корректный текст (IDE picker).
AC5: QWEN.md:42 синхронизирован с template.
AC6: Test test_mismatch_loud_warning обновлён — assert не на "/fast", а на новый actionable hint.
AC7 (negative): Banner остаётся agent-actionable — recommended model + manual switch path + persist command все на месте; agent не получает ложный совет про несуществующий programmatic switch.
AC8: pytest tests/test_task_start_model_banner.py + tests/test_model_routing.py — green.
AC9: CHANGELOG.md + CHANGELOG.ru.md — entry о fix добавлен.

## Plan

## Rollback

## Journal

- 2026-05-07T16:50:03Z [implementation] — Edits applied: scripts/model_routing.py (docstring + banner extra_lines list, drop /fast), bootstrap/bootstrap_templates.py:46 (IDE picker text), QWEN.md:42 (sync), tests/test_task_start_model_banner.py (assert on new hints), CHANGELOG.md + CHANGELOG.ru.md (Fixed sections).
- 2026-05-07T16:50:54Z [implementation] — AC verified: 1. ✓ scripts/model_routing.py:170 — verdict line says 'recommended <model> for cost savings'; '/fast' substring removed from MISMATCH verdict; only mentioned in extra_lines as explicit warning that /fast is NOT a switch 2. ✓ scripts/model_routing.py:175-179 — extra_lines.append unconditional after MISMATCH for 3 routed models (haiku/sonnet/opus); _PROFILE_SLUG_BY_MODEL_ID covers all routed ids 3. ✓ scripts/model_routing.py:1-11 — module docstring rewritten, no /fast as switch path; explicit note that /fast toggles fast-output on Opus only 4. ✓ bootstrap/bootstrap_templates.py:46 — Cost-aware model selection paragraph rewritten: IDE model picker + tausik config set + /fast disclaimer 5. ✓ QWEN.md:42 — synced manually with bootstrap_templates.py:46 (single line edit) 6. ✓ tests/test_task_start_model_banner.py:127 — assert IDE model picker + tausik config set model_profile + haiku + negative assert that switch to Haiku 4.5 via /fast substring is absent 7. ✓ Banner extra_lines provide both: manual switch path (IDE picker) + persist command (tausik config set); explicit /fast disclaimer prevents agent from re-suggesting /fast to user. Verified by test_mismatch_loud_warning + live banner output at task_start 8. ✓ pytest tests/test_task_start_model_banner.py tests/test_model_routing.py: 36 passed in 0.28s 9. ✓ CHANGELOG.md Fixed section added with Model recommendation banner entry; CHANGELOG.ru.md Исправлено section mirrored
- 2026-05-07T16:51:06Z [implementation] — AC verified: 1. ✓ scripts/model_routing.py:170 — verdict line says recommended model for cost savings; /fast substring removed from MISMATCH verdict 2. ✓ scripts/model_routing.py:175-179 — extra_lines.append unconditional after MISMATCH for 3 routed models 3. ✓ scripts/model_routing.py:1-11 — module docstring rewritten, no /fast as switch path 4. ✓ bootstrap/bootstrap_templates.py:46 — Cost-aware model selection paragraph rewritten with IDE model picker + tausik config set + /fast disclaimer 5. ✓ QWEN.md:42 — synced manually with bootstrap_templates.py:46 6. ✓ tests/test_task_start_model_banner.py:127 — assert IDE model picker + tausik config set model_profile + haiku + negative assert 7. ✓ Banner extra_lines provide manual switch path + persist command + explicit /fast disclaimer; verified by test_mismatch_loud_warning 8. ✓ pytest tests/test_task_start_model_banner.py tests/test_model_routing.py: 36 passed in 0.28s; tausik verify standard scope: passed 9. ✓ CHANGELOG.md Fixed section added; CHANGELOG.ru.md Исправлено section mirrored
