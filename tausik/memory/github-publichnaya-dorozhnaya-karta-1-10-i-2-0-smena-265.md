---
slug: github-publichnaya-dorozhnaya-karta-1-10-i-2-0-smena-265
title: "GitHub — публичная дорожная карта 1.10 и 2.0 (смена #265): milestones + issues + labels, каждая задача TAUSIK привязана github#N"
type: context
tags:
  - github
  - milestones
  - release-1.10
  - release-2.0
  - roadmap
task: null
edges: []
---

По указанию владельца («сделаем roadmap на GitHub на английском») публичная карта ведётся штатными средствами GitHub: milestone на версию (#1 «1.10 — Discipline made cheap», #2 «2.0 — Global install, no submodule»), issue на задачу (42: #9–#33 — 1.10, #34–#50 — 2.0), метка на историю (1.10:verification, 1.10:update-check, 1.10:trackers, 1.10:rag-memory, 2.0:core, 2.0:packaging, 2.0:surfaces, 2.0:client). GitHub Project (roadmap-раскладка) не создан: у токена gh нет scope project — нужен gh auth refresh -s project, если владелец захочет доску. Каждая задача TAUSIK несёт tracker_refs github#N, так что закрытие задачи предлагает закрытие issue (петля наружу 1.9). Источник правды — ROADMAP.md на линии разработки; GitHub — зеркало: новая задача в составе → новый issue с тем же milestone/label и --ticket.
