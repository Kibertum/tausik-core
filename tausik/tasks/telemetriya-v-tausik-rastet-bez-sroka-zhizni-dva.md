---
slug: telemetriya-v-tausik-rastet-bez-sroka-zhizni-dva
title: "Телеметрия в .tausik растёт без срока жизни: два jsonl на 17 МБ рядом с прореженными бэкапами"
status: done
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
relevant_files:
  - "scripts/telemetry_retention.py"
  - "tests/test_telemetry_retention.py"
  - "scripts/cmd_db.py"
  - "scripts/project_parser_db.py"
  - "scripts/project_cli_doctor.py"
  - "tausik/gates.json"
  - "docs/ru/doctor.md"
  - "docs/en/doctor.md"
scope_paths:
  - "scripts/*.py"
  - "tests/*.py"
  - "tausik/gates.json"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-28T15:01:43Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

У всякого накопительного файла в .tausik объявлен срок жизни и способ уборки, как у бэкапов БД после смены #277.

## Acceptance Criteria

1. Замер ДО: routing_adherence.jsonl и observed_coverage.jsonl, их размеры и скорость роста на смену. 2. Названы срок жизни и механизм усечения для каждого. 3. Храповик: repo_hygiene получает порог на суммарный вес накопительных файлов или их число. 4. НЕГАТИВНЫЙ: усечение не теряет запись, на которую опирается живой замер — иначе метрика молча поедет.

## Plan

## Rollback

git revert: усечение и сигнал исчезают, файлы телеметрии остаются как есть — механизм только читает и режет хвост, ничего не мигрирует.

## Journal

- 2026-09-28T14:50:37Z [implementation] — AC-1 замер ДО: файлов ТРИ, не два, на 19 MiB — routing_adherence 46192 строки, observed_coverage 54000 и ни одной записи за двадцать дней, token_metrics 8216. Ни одна строка никогда не удалялась, при том что бэкапы БД рядом прореживаются; эта асимметрия и выдала пропуск. AC-2 срок жизни следует ЧИТАТЕЛЮ: token_metrics читается по окну смен, routing_adherence сворачивается в ставку (пожизненная ставка разбавляет недавний сдвиг многомесячным средним, то есть неограниченный файл делает замер ХУЖЕ), observed_coverage не режется по возрасту — весь файл и есть замер, его перевыпускают прогоном. ПОСЛЕ: 11 MiB.
- 2026-09-28T14:58:50Z [implementation] — AC verified: 1 ✓ замер ДО и ПОСЛЕ в журнале, файлов три, 19 MiB против 11. 2 ✓ срок жизни назван по каждому файлу и следует читателю; механизм — tausik db telemetry, сухой по умолчанию, печатает объявленные сроки рядом с действием; doctor получил строку Telemetry. 3 ✓ порог в repo_hygiene.telemetry_sidecars, и он стоит на НАКОПЛЕНИИ: первая редакция порога была нарушена через минуты, потому что живая смена дописывает — записано в baseline_comment. 4 ✓ негатив: observed_coverage не режется вовсе, весь файл и есть замер; проверено тестом на файле длиной в три окна. Плюс режется ХВОСТ, а не голова. Root cause: файлы лежали рядом с прореживаемыми бэкапами, и асимметрия выдала пропуск. Domain: рабочее дерево и стоимость замеров. Negative: исключённый файл и направление обрезки закреплены. NO-DEAD-END. EVIDENCE: default 12045 passed / 30 skipped / 0 failed; mypy чистый; ставка адхеренса считается по сохранённым записям.
- 2026-09-28T15:01:39Z [implementation] — NO-DEAD-END: единственный красный прогон — bootstrap_drift на 12 развёрнутых файлах, потому что правка коснулась scripts, а профили не были переразвёрнуты. Порядок операций (редеплой ПЕРЕД закрытием, конвенция #754), а не отвергнутый подход. Отмечаю четвёртый раз за смену: ловушка устойчивее записи о ней.
