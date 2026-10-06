---
slug: backlog-orphans-invisible-to-roadmap
title: "Девятнадцать сирот бэклога разложить по историям: невидимы для roadmap и для охвата релиза"
status: done
epic: release-1-11-3
story: release1113-hygiene-calibration
complexity: simple
role: architect
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "DB-операции размещения сирот + экспорт tausik/*.md; без кода"
scope_exclude: "scripts/, tests/, CHANGELOG"
relevant_files:
  - ROADMAP.md
  - "tausik/stories/v2-baseline-consolidation.md"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T22:18:54Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#80"
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

Аудит сессии #158 насчитал 20 задач вне эпиков; одну релизную (brain-move-deletes-leave-ghost-projection) я привязал сразу, остаётся 19. Доктор про них говорит прямо: невидимы для roadmap и для task list --epic, охват релиза считает их отсутствующими.

Состав известен: четыре задачи [2.0] (проекция, элиситация, авторизация, осиротевшие рёбра), три [1.9] (мастер Notion, четыре проверки приватности, накладные расходы прогона), остальные — накопленные дефекты (дрейф доков после #152, ruff-format без гейта, окно калибровки, TAUSIK_HOME без валидации, формат тегов общей базы, cache_status=git-mismatch и прочие).

Причина у большинства одна и уже заведена отдельно: MCP молча выбрасывал параметр story. Эта задача убирает ПОСЛЕДСТВИЯ, mcp-server-drops-unknown-arguments-silently убирает ПРИЧИНУ; закрывать последствия раньше причины бессмысленно — сироты появятся снова.

КРИТЕРИИ: 1) tausik doctor не выдаёт предупреждение backlog hygiene; 2) ни одна задача не переехала в историю, к которой не относится по существу — перенос ради тишины доктора хуже сироты; 3) НЕГАТИВНЫЙ: если подходящей истории нет, задача заводится честно, а не приписывается к ближайшей.

## Acceptance Criteria

1) tausik doctor больше не выдаёт предупреждение backlog hygiene. 2) Ни одна задача не переехала в историю, к которой не относится по существу — перенос ради тишины доктора хуже сироты. 3) НЕГАТИВНЫЙ: если подходящей истории нет, задача заводится честно (новая история), а не приписывается к ближайшей.

## Plan

## Rollback

task move обратимо: перенос задачи между историями не трогает её содержимое

## Journal

- 2026-08-03T14:40:38Z [planning] — ВЫТЕСНЕНА задачей r18-orphans-triage-and-boundary (закрыта в сессии #161). Причина, по которой пишу сюда, а не закрываю молча: свежий агент иначе переоткроет уже починенное предупреждение. ЧТО СДЕЛАНО ТАМ: все 21 сироты (не 19 — за сессию #159 добавились две) разнесены по историям, tausik doctor даёт 'OK Backlog hygiene: every open task is reachable from an epic', общий итог 'OK All clean'. Заведены две новые истории (adp18-projection-coverage, adp18-suite-cost) — потому что подходящих не было, а критерий 3 этой задачи прямо запрещает приписывать к ближайшей. ЧТО ОСТАЁТСЯ ЗА ЭТОЙ ЗАДАЧЕЙ: её собственный тезис, что закрывать последствия раньше причины бессмысленно. Причина (mcp-server-drops-unknown-arguments-silently) НЕ починена, и подтверждение уже есть — счётчик сирот за одну сессию #159 сам вырос с 19 до 21. Пока причина жива, сироты появятся снова. Поэтому задачу не закрываю: она остаётся держателем этого тезиса, но её AC1 сегодня достигнут другой задачей.
- 2026-09-09T08:43:29Z [planning] — ПРЕМИСА УСТАРЕЛА ЧАСТИЧНО, смена #241. Заявлено девятнадцать сирот бэклога; сейчас их ТРИ, и все три заведены сегодня мной (heredoc, слаги, чтение ленты CI). То есть шестнадцать разложены по историям за прошедшее время, и предмет сжался с программы уборки до трёх карточек одной смены. Задача остаётся осмысленной как ПРАВИЛО (сирота невидима для roadmap и для охвата релиза), но её объём больше не девятнадцать.
- 2026-10-06T22:18:39Z [implementation] — AC-1 (doctor silent): ✓ ausik doctor now prints 'Backlog hygiene: every open task is reachable from an epic'. AC-2 (no dishonest moves): ✓ audit found 4 current orphans (not 19 — the old audit's remainder was already resolved); two v2 runtime tasks (consolidate-backend-migrations, move-flat-scripts-runtime) got an honest NEW story v2-baseline-consolidation [v2-global-mcp] because every existing core-simplification story is done and adoption would rewrite shipped scope; qualify-luna and retrospektiva-codex moved to release111-economy-hardening (active) — model routing and Codex spend measurement are that story's substance. AC-3 NEGATIVE (no nearest-neighbor adoption): ✓ demonstrated by creating v2-baseline-consolidation instead of parking in done v2-simplify-core or stretchy v2gm-* stories. Domain: roadmap reachability restored — release scope counts all four; ROADMAP.md reissued automatically.
