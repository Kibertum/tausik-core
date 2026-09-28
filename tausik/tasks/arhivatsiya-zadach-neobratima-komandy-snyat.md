---
slug: arhivatsiya-zadach-neobratima-komandy-snyat
title: "Архивация задач необратима: команды снять archived_at нет, а Rollback обещает обратное"
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

Мягкая архивация задач обратима командой, как обещает её же спецификация и Rollback задач, которые на неё ссылаются. Сейчас снять archived_at нельзя ничем, кроме прямого SQL, а прямой доступ к БД проекту запрещён.

## Acceptance Criteria

1. Замер ДО: путей, снимающих archived_at, ноль — ни у задач, ни у памяти; при этом Rollback задачи о гигиене обещает обратимость командой. 2. Команда снимает archived_at по слагу и по возрасту, с сухим прогоном. 3. НЕГАТИВНЫЙ: разархивация не меняет status и completed_at — она снимает признак скрытия, а не оживляет задачу. 4. Спецификация и Rollback перестают обещать то, чего нет: либо команда есть, либо обещание убрано.

## Plan

## Rollback

## Journal
