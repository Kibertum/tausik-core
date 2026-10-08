---
slug: github-roadmap-kak-v-harvester-milestone-vx-y-z-kind
title: "GitHub roadmap — как в Harvester: milestone vX.Y.Z, [KIND]-заголовки, kind/area/priority, [EPIC] с sub-issues; без Projects"
type: convention
tags:
  - convention
  - epics
  - github
  - milestones
  - roadmap
task: null
edges: []
---

По указанию владельца (смена #265, «как в harvester/harvester») публичная карта на GitHub ведётся ТОЛЬКО штатными сущностями, без Projects (проект #4 удалён): milestone = релиз с именем тега (v1.10.0, v2.0.0; описание — вопрос версии и обещания); issue = задача с префиксом [BUG]/[TASK]/[FEATURE]/[ENHANCEMENT]/[REFACTOR] и метками kind/*, area/*, priority/0-2 (только где известен), severity/1 для багов, бьющих всех; [EPIC] на историю (kind/epic) — sub-issues через GraphQL addSubIssue, прогресс считает GitHub сам. Карта читается по ссылке issues?q=is:issue state:open milestone:v1.10.0. Соответствие: 1.10 — epics #52–#55 (A verify, B update, C trackers, D rag/memory), задачи #9–#33 и #51; 2.0 — epics #56–#59, задачи #34–#50. Каждая задача TAUSIK несёт tracker_refs github#N. Правило поддержки: новая задача в составе → issue с тем же milestone, kind/area, sub-issue своего EPIC и --ticket github#N; новая история → [EPIC]. Источник правды — ROADMAP.md на линии разработки; GitHub — зеркало. Не делать: Projects-доски (не понравилось владельцу), метки с номером релиза в имени (это milestone).
