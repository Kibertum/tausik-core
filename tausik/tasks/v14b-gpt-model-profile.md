---
slug: v14b-gpt-model-profile
title: "B8: TAUSIK_MODEL_PROFILE enum — добавить gpt-4, gpt-5, gpt-5.5"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "harness/skills/{plan,task,ship}/variants/, tests/test_skill_profile.py, docs/en/skill-profiles.md, docs/ru/skill-profiles.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/skill_profile.py (уже работает с любым slug), bootstrap_config.py (slug normalize уже принимает gpt-5.5)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T00:41:21Z"
---

## Goal

Сейчас TAUSIK_MODEL_PROFILE поддерживает только claude/qwen variants. Cursor работает с GPT-4/5/5.5. Расширить enum + создать variants/{gpt-4,gpt-5}.md для /plan, /task, /ship — GPT prefers tool calls over reasoning, шире tool calls, меньше narrative.

## Acceptance Criteria

1. Созданы 9 overlay-файлов в harness/skills/{plan,task,ship}/variants/{gpt-4,gpt-5,gpt-5-5}.md — каждый отражает GPT-стиль (prefer tool calls > narrative reasoning, terse, parallel tool calls). 2. tests/test_skill_profile.py: parametrized тест проверяет, что merge_skill_markdown подмешивает overlay для каждой комбинации (skill × profile) и base остается. 3. tests/test_skill_profile.py: negative — unknown slug 'gpt-99' возвращает только base без exception. 4. tests/test_skill_profile.py: TAUSIK_MODEL_PROFILE='gpt-5.5' (с точкой) после normalize_model_profile_slug → 'gpt-5-5' и резолвит правильный overlay. 5. Документация (docs/en/skill-profiles.md + docs/ru/skill-profiles.md): добавлен gpt-4/gpt-5/gpt-5-5 в список known profiles. 6. CHANGELOG.md + CHANGELOG.ru.md: запись в Unreleased — 'Added GPT model profile variants (gpt-4, gpt-5, gpt-5-5) for /plan, /task, /ship'. 7. ruff + mypy + filesize gates green; pytest test_skill_profile.py зелёный.

## Plan

[{"step": "1. Create 9 overlay files: harness/skills/{plan,task,ship}/variants/model/{gpt-4,gpt-5,gpt-5-5}.md with GPT-style telegraphic instructions", "done": true}, {"step": "2. Extend tests/test_skill_profile.py: parametrized test verifies merge_skill_markdown applies overlay for each (skill x gpt-profile) combo and base remains", "done": true}, {"step": "3. Add tests: unknown 'gpt-99' returns base only; 'gpt-5.5' normalizes to 'gpt-5-5' and resolves overlay", "done": true}, {"step": "4. Update docs/{en,ru}/skill-profiles.md: list gpt-4/gpt-5/gpt-5-5 in known model profiles", "done": true}, {"step": "5. CHANGELOG en+ru: entry under Unreleased v1.4 polish", "done": true}, {"step": "6. ruff + mypy + pytest + filesize gates green; regen constants.json if test count changed", "done": true}]

## Rollback

## Journal

- 2026-05-06T22:31:00Z [implementation] — Blocked: dead-end realization. Writing variants/{gpt-4,gpt-5,gpt-5-5}.md без механизма авто-детекции модели → файлы никогда не загрузятся (никто не выставит TAUSIK_MODEL_PROFILE=gpt-5 вручную). Также variants/ сейчас смешивает две оси: IDE (claude/cursor/qwen/codex — детектится) и модель внутри IDE (haiku/sonnet/gpt-N — не детектится; Cursor крутит и Claude, и GPT). Семантика gpt-5.md плывёт. Нужны: 1) auto-detect + interactive prompt в `tausik init`; 2) решение по axis (variants/ это про модель, про IDE, или гибрид типа `cursor-gpt-5.md`). До этого B8 — мёртвый код. См. v14b-model-profile-detection.
- 2026-05-07T00:41:16Z [implementation] — AC verified: 1. ✓ 9 overlay files created (3 skills × 3 gpt profiles) telegraphic delta-only style ≤25 lines each. 2. ✓ tests/test_skill_profile.py::test_gpt_overlays_resolve_for_each_skill parametrized 9 cases (skill × profile) — base remains + overlay merged. 3. ✓ tests/test_skill_profile.py::test_unknown_gpt_profile_returns_base_only — gpt-99 returns base only, no exception. 4. ✓ tests/test_skill_profile.py::test_gpt_5_5_dot_normalizes_to_hyphen — gpt-5.5 → gpt-5-5 resolves overlay. 5. ✓ docs/{en,ru}/skill-profiles.md updated with gpt-4/gpt-5/gpt-5-5 in known model profiles + design intent block. 6. ✓ CHANGELOG.md + CHANGELOG.ru.md entry under Unreleased v1.4 polish. 7. ✓ ruff All checks passed; pytest 44 passed (skill_profile + gen_doc_constants); filesize gates green (overlay files all ≤25 lines).
