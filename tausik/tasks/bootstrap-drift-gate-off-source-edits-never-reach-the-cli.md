---
slug: bootstrap-drift-gate-off-source-edits-never-reach-the-cli
title: "Гейт bootstrap_drift ВЫКЛЮЧЕН — правка в scripts/ не доезжает до работающего CLI и MCP, и об этом никто не узнаёт"
status: planning
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО ЗАМЕРОМ #191-БД, ПОБОЧНО. Закрыв задачу о новом гейте claudemd_state_drift, я увидел, что он НЕ ПОЯВИЛСЯ в списке гейтов task-done, хотя объявлен в scripts/gate_registry.py и его тесты зелёные. Причина: `.tausik/tausik` — обёртка, которая исполняет код из РАЗВЁРНУТОГО профиля (.claude/scripts/, первый существующий из claude/cursor/windsurf/codex/qwen/kilo/opencode), а не из scripts/. То же и у MCP-сервера. Правка в scripts/ вступает в силу только после `python bootstrap/bootstrap.py --ide all`. Записано памятью #438.

ЧТО ИМЕННО МОЛЧАЛО. Гейт bootstrap_drift существует ровно для этого («Fail if deployed IDE profiles drift from scripts/ source», severity=block, trigger=task-done) и в этом проекте стоит [OFF]. То есть страж, поставленный против «правка не вступила в силу», сам выключен, и отказ невидим: тесты зелёные (они импортируют из scripts/), гейты зелёные (они исполняются из .claude/), и обе стороны говорят правду о разном коде.

ЦЕНА, ЗАМЕРЕННАЯ, А НЕ ПРЕДПОЛОЖЕННАЯ. `bootstrap.py --check --ide all` показал 15 дрейфующих файлов в пяти профилях, и среди них НЕ ТОЛЬКО новый гейт: там gate_command_runner.py, то есть починка инъекции полной ленты (TAUSIK_VERIFY_FULL=1 подставляет -m '' вместо стирания addopts), УЖЕ ЗАКОММИЧЕННАЯ в 6b81b78, до работающего CLI не доехала. Закрытая и оплаченная работа лежала неисполняемой.

ЧТО ДЕЛАЕТСЯ: понять, ПОЧЕМУ гейт выключен (осознанное решение или тихий дефолт), и либо включить, либо заменить механизмом, который не требует ручного bootstrap. НЕГАТИВНОЕ, ОБЯЗАТЕЛЬНОЕ: правка scripts/gate_registry.py без последующего bootstrap обязана ОТКАЗАТЬ закрытие задачи, а не закрыть его зелёным — проверяется мутацией: внести правку в источник, не разворачивать, убедиться, что task-done краснеет.

СМЕЖНОЕ: claudemd-drift-gates-do-not-notice-an-emptied-dynamic-block (эта задача найдена внутри неё), claudemd-dynamic-block-wiped-to-an-empty-project.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-08-30T20:18:02Z [planning] — [#191-БД] ВТОРОЙ СЛОЙ ТОГО ЖЕ ОТКАЗА, ЗАМЕРЕН ПРЯМО ПРИ ЗАКРЫТИИ ЗАДАЧИ: РАЗВЁРНУТЬ ПРОФИЛЬ НЕДОСТАТОЧНО, ПОКА ЖИВ СТАРЫЙ ПРОЦЕСС MCP. После `bootstrap --ide all` команда `.tausik/tausik gates status` (свежий процесс) показывает «[ON] claudemd_state_drift (block) -> task-done, commit». Но закрытие задачи ЧЕРЕЗ MCP в той же сессии дважды подряд отработало БЕЗ этого гейта: в списке шли filesize, class_surface, memory_route, renar_drift_schema, renar_drift_provenance, skill_spec_conformance — и всё. Причина: сервер MCP запущен ДО развёртывания и держит реестр гейтов в памяти своего процесса. СЛЕДСТВИЕ ДЛЯ ЭТОЙ ЗАДАЧИ: цепочка «правка в scripts/ → bootstrap → гейт действует» имеет ТРИ звена, а не два, и третье (перезапуск сервера MCP) сегодня не выражено нигде и не проверяется ничем. Агент, работающий по правилу MCP-first, получает зелёные закрытия по СТАРОМУ набору гейтов и не имеет способа это заметить: обе стороны молчат. ЧТО ЭТО ЗНАЧИТ ДЛЯ ОБЪЁМА ЗАДАЧИ: включить bootstrap_drift — необходимо, но НЕ достаточно. Нужен ещё признак «набор гейтов в работающем сервере отличается от набора в источнике», иначе останется ровно та же дыра, только на одно звено дальше. ПРОВЕРКА ДЛЯ СЛЕДУЮЩЕГО: сравнить вывод `.tausik/tausik gates status` (свежий процесс, читает развёрнутый профиль с диска) со списком гейтов в JSON-ответе tausik_task_done (живой процесс MCP). Расхождение = сервер устарел.
