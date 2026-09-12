---
slug: normalize-release-backlog-19-110-20
title: "Нормализовать backlog по релизам 1.9, 1.10 и 2.0"
status: done
epic: null
story: null
complexity: complex
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: "Do not modify product code, bootstrap behavior, tests, release metadata, tag, push or user-owned .agents/."
relevant_files:
  - ROADMAP.md
  - "tests/test_release_roadmap.py"
scope_paths:
  - "tausik/tasks/*.md"
  - "tausik/stories/*.md"
  - "tausik/epics/*.md"
  - ROADMAP.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-12T13:37:19Z"
---

## Goal

Сделать каждый незакрытый элемент backlog однозначно относимым к 1.9, 1.10, 2.0 или доказанно закрытым как superseded/неактуальный; сохранить решения владельца и не менять продуктовый код, релиз, тег или публикацию.

## Acceptance Criteria

AC-1: каждый незакрытый task и story имеет явную судьбу: 1.9, 1.10, 2.0 или закрыт как superseded с причиной и ссылкой на решение/измерение. AC-2: состав 1.9 ограничен решениями #358, #360 и #361; не названные ими инициативы не остаются неявными блокерами. AC-3: 2.0 содержит только global MCP и client; любое другое незавершённое направление вынесено в 1.10. AC-4: ложные или потерявшие предмет задачи закрыты без объявления выполненной функциональности; отрицательный сценарий: brainh-reliability не переносится в 1.10, поскольку Notion удаляется решением #358. AC-5: итоговая release map и порядок зависимостей записаны в канонических backlog-артефактах, проверены штатными командами, без product-code/release/tag/push.

## Plan

[{"step": "\u0421\u043e\u0431\u0440\u0430\u0442\u044c \u043f\u043e\u043b\u043d\u044b\u0439 \u0438\u043d\u0432\u0435\u043d\u0442\u0430\u0440\u044c \u043d\u0435\u0437\u0430\u043a\u0440\u044b\u0442\u044b\u0445 epic/story/task \u0438 \u0438\u0445 \u0442\u0435\u043a\u0443\u0449\u0438\u0435 \u0441\u0432\u044f\u0437\u0438 \u0441 \u0440\u0435\u043b\u0438\u0437\u0430\u043c\u0438.", "done": true}, {"step": "\u0421\u0432\u0435\u0440\u0438\u0442\u044c \u043a\u0430\u0436\u0434\u044b\u0439 \u044d\u043b\u0435\u043c\u0435\u043d\u0442 \u0441 \u0440\u0435\u0448\u0435\u043d\u0438\u044f\u043c\u0438 \u0432\u043b\u0430\u0434\u0435\u043b\u044c\u0446\u0430, \u0444\u0430\u043a\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u043c\u0438 \u0437\u0430\u0432\u0438\u0441\u0438\u043c\u043e\u0441\u0442\u044f\u043c\u0438 \u0438 \u0443\u0436\u0435 \u043e\u0442\u043c\u0435\u0447\u0435\u043d\u043d\u044b\u043c\u0438 \u043f\u0435\u0440\u0435\u043d\u043e\u0441\u0430\u043c\u0438.", "done": true}, {"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0438\u043b\u0438 \u0443\u0442\u043e\u0447\u043d\u0438\u0442\u044c \u043a\u0430\u043d\u043e\u043d\u0438\u0447\u0435\u0441\u043a\u0438\u0435 1.10 \u0438 2.0 \u043a\u043e\u043d\u0442\u0435\u0439\u043d\u0435\u0440\u044b, \u0437\u0430\u0442\u0435\u043c \u043f\u0435\u0440\u0435\u043c\u0435\u0441\u0442\u0438\u0442\u044c \u0442\u043e\u043b\u044c\u043a\u043e \u0434\u043e\u043a\u0430\u0437\u0430\u043d\u043d\u043e \u043d\u0435\u0440\u0435\u043b\u0438\u0437\u043d\u044b\u0435 \u044d\u043b\u0435\u043c\u0435\u043d\u0442\u044b.", "done": true}, {"step": "\u0417\u0430\u043a\u0440\u044b\u0442\u044c \u043a\u0430\u043a superseded \u0437\u0430\u0434\u0430\u0447\u0438 \u0441 \u043e\u043f\u0440\u043e\u0432\u0435\u0440\u0433\u043d\u0443\u0442\u043e\u0439 \u043f\u0440\u0435\u0434\u043f\u043e\u0441\u044b\u043b\u043a\u043e\u0439 \u0438\u043b\u0438 \u0441\u043d\u044f\u0442\u044b\u043c \u043f\u0440\u0435\u0434\u043c\u0435\u0442\u043e\u043c, \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0432 \u043f\u0440\u0438\u0447\u0438\u043d\u0443.", "done": true}, {"step": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u0435 \u0441\u0438\u0440\u043e\u0442, \u043f\u0440\u043e\u0442\u0438\u0432\u043e\u0440\u0435\u0447\u0438\u0432\u044b\u0445 \u0440\u0435\u043b\u0438\u0437\u043d\u044b\u0445 \u043c\u0435\u0442\u043e\u043a \u0438 \u043d\u0435\u044f\u0432\u043d\u044b\u0445 \u0431\u043b\u043e\u043a\u0435\u0440\u043e\u0432; \u0437\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0438\u0442\u043e\u0433\u043e\u0432\u0443\u044e \u043a\u0430\u0440\u0442\u0443 \u0438 \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c signed verify.", "done": true}]

## Rollback

Revert the dedicated backlog-normalization commit; task-state changes are restored by the framework task exports and audit log.

## Journal

- 2026-09-12T10:37:14Z [implementation] — Спецификация владельца: backlog обязан быть релизной картой. Незакрытое относится только к 1.9, 1.10 или 2.0; 2.0 ограничен global MCP и client. Потерявшие предмет задачи закрываются/supersede, а не переносятся. Состав 1.9 фиксируется решениями #358/#360/#361. Никакого product-code, тега, push или релиза.
- 2026-09-12T10:39:01Z [implementation] — Инвентарь: 180 незакрытых задач (163 planning, 15 blocked, 2 active) и несколько активных исторических эпиков. Ядро 1.9 берётся только из решений #358/#360/#361; 2.0 — только v2-global-mcp и клиентский контур. Выявлены уже помеченные 1.10 истории и восемь неявных старых историй, которые пока искажают 1.9.
- 2026-09-12T10:40:40Z [implementation] — Сверка с #358/#360/#361 завершена: 79 плановых задач сняты с историй release-19, не входящих в утверждённое ядро, и разложены по шести историям 1.10. Истории с перенесённым или отсутствующим pending work закрыты как завершённые контейнеры, не как выполненная отложенная функциональность.
- 2026-09-12T10:43:36Z [implementation] — Создан явный 2.0 client container universal-vscode-extension/v2-client-extension. В него перенесены только extension/provisioning/migration задачи; skill web catalog остаётся 1.10, поскольку это позиционирование, а не клиент. Все найденные незакрытые задачи вне 1.9 и 2.0 теперь разнесены по 1.10.
- 2026-09-12T10:44:35Z [implementation] — Supersession records were prepared for brainh-reliability, brainh-audit and the false GitHub-trigger task. Their terminal QG-2 closures were correctly refused because the shared tree has uncommitted work (including user-owned .agents/); no false fileless closure was made. They will be closed after the scoped backlog-state commit, using the recorded terminal evidence.
- 2026-09-12T10:45:01Z [implementation] — Закрыты пустые исторические контейнеры arch-debt-post-18, landscape-2026-h2, research-with-a-death-date, visibility-stream, standards-window, brain-hardening и vscode-extension после переноса их pending задач. Они не содержат скрытых релизных обязательств.
- 2026-09-12T10:45:27Z [implementation] — Обнаружен legacy epic universal-vscode-extension со статусом done; чтобы 2.0 client не висел внутри закрытого контейнера, создан явный active epic v2-client/v2-client-delivery и три клиентские задачи перенесены туда. Старый пустой контейнер закрыт.
- 2026-09-12T10:47:30Z [implementation] — Закрыты пустые active/open stories, включая v14-polish follow-up и legacy 1.3/1.5 контейнеры. Empty 1.10 context story также закрыта: контекстный объём 1.10 не потерян, но сейчас не имеет задач и не должен выглядеть обязательством.
- 2026-09-12T13:15:47Z [implementation] — call_budget re-estimated 150→60 in session #244: steps 1-3 are done and committed (e2f55369); the remaining work is three supersession closures, the orphan/label check and one signed verify. The 150 planned calls were holding the whole session capacity (remaining 1/200) and blocking the start of a release-critical defect task.
- 2026-09-12T13:35:17Z [implementation] — AC verified: AC-1 ✓ every open task/story has a release (map above; superseded ones closed with reason and decision refs). AC-2 ✓ 1.9 composition equals decisions #358/#360/#361 — no other initiative remains an implicit blocker. AC-3 ✓ 2.0 holds only v2-global-mcp and v2-client tracks. Negative: the kb-docs-* trio stays inside the 1.9 Notion-shedding story rather than being silently deferred — its release label is a pending owner call named in the handoff, not a hidden default. Domain: ROADMAP.md regenerated from this state passes tests/test_release_roadmap.py (30/30).
- 2026-09-12T13:35:17Z [implementation] — Step 5 map (session #244, after 15 closures today): 1.9 = release19-proof-integrity (open: scoped-pytest, blocked), release19-effective-context (open: 5 planning — response-contract-sets-a-shape, r-does-our-injected-context-block-earn-its-cost, response-contract-adherence-is-never-measured, compaction-contract-lives-in-claude-md, memory-is-retrieved-by-relevance-not-recency; v14b-rag-nudge-replay-benchmark blocked), codex-first-class-19 (open: codex-live-acceptance-proves-the-host, blocked on nothing since the pathlib fix closed), knowledge-sheds-notion-and-its-hygiene (open: remove-the-notion-wizard-token-cascade-and-project-registry [1.9], unify-the-four-privacy-checks-into-one-publication-boundary [1.9], kb-docs-map, kb-docs-swarm, kb-docs-consistency). 1.10 = five deferred-110-* stories, 135 planning tasks. 2.0 = v2gm-core/surfaces/packaging (14) + v2-client-delivery (3). Orphans: none (this task is the only story-less open task, by design). Superseded terminally: brainh-reliability, brainh-audit, ci-lane-runs-on-main-only-so-the-release-branch-is. Contradictory labels: none found — every open task sits in a story whose epic names its release; four stories in 1.9 epics carry a [ПЕРЕНЕСЕНО В 1.10] title and are done as containers.
