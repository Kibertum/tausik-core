---
slug: github-milestone-planning-smena-265-105-issue-otlozhennogo
title: "GitHub milestone Planning (смена #265): 105 issue отложенного бэклога, четыре задачи признаны устаревшими и не опубликованы"
type: context
tags:
  - backlog
  - github
  - planning
  - roadmap
task: null
edges: []
---

Смена #265, по указанию владельца («планнинг сделаем обязательно; дат у нас нет»). Milestone «Planning» (#3) — весь открытый бэклог линии разработки, который не назван ни одним составом релиза: 105 issue (#60–#164) из пяти корзин deferred-110-*, каждая с [KIND]-префиксом, kind/* и area/*, в теле — исходное русское название и слаг задачи; каждая задача несёт tracker_refs github#N. Дат у milestones нет намеренно. Не опубликованы четыре задачи (закрыть на линии разработки, а не публиковать): full-suite-runs-only-in-ci-and-ci-has-not-run (CI гоняется с 14.09), pr5-was-promised-a-merge-and-planned-as-a-reimplementation (PR #5 перенесён и закрыт), the-routing-table-names-two-of-four-stores (GitLab #6 починен), rule-on-ruff-016-new-defaults-1539-findings (дубль #85). Правило: новая задача вне состава → issue в Planning; перенос в релиз = смена milestone + sub-issue эпика по решению владельца. Итог на GitHub: v1.10.0 — 30, v2.0.0 — 21, Planning — 105.
