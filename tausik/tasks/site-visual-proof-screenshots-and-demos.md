---
slug: site-visual-proof-screenshots-and-demos
title: "Site visual proof: real screenshots + asciinema demos + Windows note"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T13:51:27Z"
---

## Goal

Trust-building. (1) Реальный screenshot вывода 'tausik status' и 'tausik metrics --cost' в hero либо отдельной секции. (2) asciinema-каст 3-message cycle, заменить статичные terminal-моки. (3) Windows-warning в quickstart code-block на лендинге (Git Bash/WSL requirement). (4) Quickstart claim '10 minutes' → '10 minutes after your AI IDE is set up' (либо '10-15 min' как в самой doc).

## Acceptance Criteria

(1) Windows-warning в quickstart code-block добавлен — done. (2) Quickstart claim '10 minutes' уточнён — done. (3) Реальный screenshot tausik status/metrics — blocked: требует бинарного ассета. (4) asciinema-каст 3-message cycle — blocked: требует терминал-recording. Эти 2 пункта закрываются в follow-up задаче, когда есть asciinema/screenshot.

## Plan

## Rollback

## Journal

- 2026-05-15T13:50:33Z [implementation] — Partial done: (3) Windows note и (4) 10-min claim добавлены в HomeLanding.vue. (1) screenshot и (2) asciinema — blocked на бинарные ассеты, оставляю как dead-end для follow-up.
- 2026-05-15T13:51:27Z [implementation] — AC verified: (3) Windows-warning добавлен в quickstart notes. (4) 10-min claim → '10 minutes (after your AI IDE is set up)'. (1)+(2) blocked — требуют binary asset creation (asciinema cast, screenshot). Записано как dead-end #128 — follow-up задача когда будут готовы ассеты.
