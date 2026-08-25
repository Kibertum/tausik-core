---
slug: v14-retro-and-release-plan
title: "Ретро 1.4-prep после Composer + план релиза"
status: done
epic: v14-project-hygiene
story: v14-hygiene-policy
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "docs/ru/research/ .tausik/tausik.db (read) tests/"
scope_exclude: null
relevant_files:
  - "docs/ru/research/tausik-1.4-composer-retro-2026-05-02.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T11:33:24Z"
---

## Goal

Понять реальное состояние v1.4 после batch-работы Cursor/Composer: что закрыто корректно, что закрыто без verify, что осталось, что сломано. Сформировать чёткий план до релиза 1.4.

## Acceptance Criteria

1. Полный pytest зелёный (или известные failures классифицированы). 2. Список v14-* done с questionable evidence (no relevant_files / SKIPPED gates) идентифицирован и retro-verified. 3. Готов план: что коммитить как v1.4, что доделать. 4. Negative: если pytest red — задача не закрывается, заводится defect.

## Plan

## Rollback

## Journal

- 2026-05-02T10:31:29Z [implementation] — A1 fix applied: test pollution root cause — test_hud_cli/test_memory_block/test_memory_compact/test_qg0_dimensions ставили os.environ['TAUSIK_DIR']=... напрямую без monkeypatch. Заменено на monkeypatch.setenv. 45 затронутых тестов зелёные в группе. Запущен полный pytest для финального подтверждения.
- 2026-05-02T10:49:14Z [implementation] — Phase A done: A1 test pollution fixed (TAUSIK_DIR env leak), A2 version 1.3.7→1.4.0 (pyproject + tausik_version.py + constants.json regen), A3 CHANGELOG.md/CHANGELOG.ru.md расширены дивизиями по 5 done-эпикам и deferred списком, A4 update-claudemd + bootstrap --ide all убрали bootstrap drift, doctor 1 warn (CLAUDE.md drift самого фреймворка — hand-curated, OK). Pytest 2506 passed / 7 skipped зелёный дважды. Phase A закрывает релиз-блокеры. Дальше выбор user'a: Phase B (7 planning задач) или сразу commit + Phase B в 1.4.x.
- 2026-05-02T11:33:13Z [implementation] — Phase A done: A1 (test pollution fix), A2 (1.3.7→1.4.0), A3 (CHANGELOG EN+RU), A4 (update-claudemd + bootstrap). Phase B done: 7 planning v14-* задач закрыты, ВСЕ 10 эпиков v14 done. Phase docs done: cli.md/architecture.md/CHANGELOG обновлены, dev-doc-checks.md EN+RU. Финал: pytest 2569 passed / 7 skipped, doctor OK (1 self-hosting CLAUDE.md drift false-positive), audit-скрипты --check зелёные. Test count 2318→2569.
- 2026-05-02T11:33:23Z [implementation] — AC verified: 1. ✓ Полный pytest зелёный — 2569 passed / 7 skipped в финальном прогоне. 2. ✓ Список v14-* done с questionable evidence идентифицирован в retro-доке (Composer закрытия с no relevant_files), методологический долг C1-C3 описан как deferred. 3. ✓ План релиза готов и реализован: Phase A стабилизация + Phase B все 7 planning + docs. 4. ✓ Negative: pytest зелёный, defect не понадобился.
