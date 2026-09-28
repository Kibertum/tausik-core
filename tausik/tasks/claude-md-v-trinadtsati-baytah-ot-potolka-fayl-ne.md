---
slug: claude-md-v-trinadtsati-baytah-ot-potolka-fayl-ne
title: "CLAUDE.md в тринадцати байтах от потолка: файл не принимает нового указателя"
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
tracker_refs: []
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

У CLAUDE.md есть запас на следующий указатель, и правило, по которому в нём что-то появляется, объявлено. Замер: статическая часть 4083 из 4096 байт до этой уборки — тринадцать байт, то есть один указатель не влезал, и потолок молча превращался в запрет на любое дополнение.

## Acceptance Criteria

1. Замер ДО и ПОСЛЕ: байты статической части, и что именно освободило место. 2. Названо правило, ЧТО имеет право стоять в CLAUDE.md: ограничение, которое агент нарушает по умолчанию, против справочной прозы — второе живёт в docs. 3. Дубли указателей убраны: один адрес называется один раз. 4. НЕГАТИВНЫЙ: сокращение не выбрасывает ни одного жёсткого ограничения — сравнение списка ограничений до и после, он обязан совпасть.

## Plan

## Rollback

## Journal
