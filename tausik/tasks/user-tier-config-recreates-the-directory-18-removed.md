---
slug: user-tier-config-recreates-the-directory-18-removed
title: "Пользовательский тир конфига воссоздаёт каталог, который 1.8 убирала ломающим изменением"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: complex
role: backend
stack: null
tier: moderate
call_budget: 55
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/config_trust.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/gate_toggle.py"
  - "tests/test_user_tier_location.py"
scope_paths:
  - "scripts/config_trust.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/gate_toggle.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T08:11:12Z"
resolution: null
resolution_reason: null
---

## Goal

Настройка пользовательского тира не требует создавать ~/.tausik/ — каталог, из-за которого обнаружение проекта считает домашнюю папку проектом, — и обнаружение больше не принимает за проект каталог без базы.

## Acceptance Criteria

1. Замер, с которого всё началось, воспроизведён: на машине владельца существует ~/.tausik/ и содержит ТОЛЬКО config.json. Обнаружение проекта (find_tausik_dir, project_config.py:132) ищет каталог с именем .tausik и НЕ проверяет наличие базы — значит домашняя папка становится проектом для всего, что под ней и не имеет своего .tausik выше по дереву.
2. Названо, что это НЕ новый дефект, а возврат старого: ломающее изменение 2 в 1.8 перенесло общую базу знаний из ~/.tausik/ именно по этой причине, а whats-new 1.8 в разделе про изменение 3 САМА предупреждает, что настройка пользовательского тира создаст этот каталог заново. Мы задокументировали ловушку и живём в ней.
3. Путь пользовательского тира по умолчанию перенесён туда, где он не создаёт .tausik (например ~/.config/tausik/config.json или ~/.tausik-config/). Старое расположение продолжает ЧИТАТЬСЯ, чтобы не отнять настройку у тех, кто её уже сделал.
4. Обнаружение проекта ужесточено: каталог .tausik без базы и без признаков проекта не считается корнем проекта — либо считается, но ГОВОРИТ об этом вслух, а не молча.
5. Предупреждение в whats-new 1.8 и в config-trust-tiers обновлено: обходной путь через TAUSIK_USER_CONFIG перестаёт быть единственным ответом.
6. НЕГАТИВНЫЙ сценарий: тест на раскладку «домашняя папка содержит .tausik только с конфигом, рабочий каталог под ней без своего .tausik» — обнаружение НЕ должно молча объявить домашнюю папку проектом.
7. НЕГАТИВНЫЙ сценарий: миграция не отнимает существующие настройки. Тест на то, что старое расположение всё ещё читается и что при наличии обоих побеждает новое с явным сообщением.

## Plan

## Rollback

git revert коммита; путь пользовательского тира возвращается прежним, миграция читает оба места

## Journal

- 2026-09-24T07:54:05Z [implementation] — AC-1: ✓ measurement — owner's machine: ~/.tausik holds config.json (+ a .bak) and nothing else; find_tausik_dir already refuses the home tier dir (forbidden = realpath of ~/.tausik) and stops at home.
- 2026-09-24T07:54:05Z [implementation] — AC-2: ✓ review — named as the return of the 1.8 trap the whats-new-1.8 note itself warned about.
- 2026-09-24T07:54:05Z [implementation] — AC-3: ✓ tests/test_user_tier_location.py::test_nothing_configured_points_at_the_new_place — config_trust.default_user_config_path = ~/.config/tausik/config.json; legacy_user_config_path kept for reading.
- 2026-09-24T07:54:06Z [implementation] — AC-4: ✓ tests/test_user_tier_location.py::test_a_home_tausik_with_only_a_config_is_not_a_project — discovery does not adopt the home .tausik; doctor names the legacy location out loud (User tier line).
- 2026-09-24T07:54:06Z [implementation] — AC-5: ✓ review — docs/*/config-trust-tiers.md name the new path and the legacy read; gate_toggle's refusal text names the new path; whats-new 1.8/1.9 left as history.
- 2026-09-24T07:54:06Z [implementation] — AC-6: ✓ tests/test_user_tier_location.py::test_a_home_tausik_with_only_a_config_is_not_a_project — negative.
- 2026-09-24T07:54:07Z [implementation] — AC-7: ✓ tests/test_user_tier_location.py::test_a_legacy_only_setting_is_still_read and tests/test_user_tier_location.py::test_the_new_place_wins_when_both_exist — negative; 786 config/doctor/toggle tests green.
- 2026-09-24T08:02:05Z [implementation] — NO-DEAD-END: the refused closes were doc_coverage asking for the new doctor line 'User tier' in docs/*/doctor.md — added; not an approach error.
