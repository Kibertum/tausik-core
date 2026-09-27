---
slug: telemetriya-v-tausik-rastet-bez-sroka-zhizni-dva
title: "Телеметрия в .tausik растёт без срока жизни: два jsonl на 17 МБ рядом с прореженными бэкапами"
status: planning
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
---

## Goal

У всякого накопительного файла в .tausik объявлен срок жизни и способ уборки, как у бэкапов БД после смены #277.

## Acceptance Criteria

1. Замер ДО: routing_adherence.jsonl и observed_coverage.jsonl, их размеры и скорость роста на смену. 2. Названы срок жизни и механизм усечения для каждого. 3. Храповик: repo_hygiene получает порог на суммарный вес накопительных файлов или их число. 4. НЕГАТИВНЫЙ: усечение не теряет запись, на которую опирается живой замер — иначе метрика молча поедет.

## Plan

## Rollback

## Journal
