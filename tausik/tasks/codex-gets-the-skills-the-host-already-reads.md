---
slug: codex-gets-the-skills-the-host-already-reads
title: "Навыки доставляются в .codex/skills — хост их читает, а каталога нет вовсе"
status: planning
epic: release-19-renar-conformance
story: codex-is-a-first-class-host
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
completed_at: null
---

## Goal

ЗАМЕР, смена #241. Codex читает .codex/skills и SKILL.md - обе строки присутствуют в бинаре codex.exe, как и .codex/agents. В проекте уже лежит .codex/agents с четырьмя файлами .toml, но каталога .codex/skills нет вовсе: навыки под Codex не доставляются, потому что codex отсутствует в SCAFFOLD_IDES и генератора для него нет.

ЧТО ДЕЛАЕТСЯ. Раскладка активных навыков в .codex/skills/ тем же путём, каким они кладутся остальным хостам, и с тем же профилем (IDE-оверлей codex у skill_profile уже существует - см. VALID_IDES в skill_profile_detect). Каталог .codex/ в .gitignore, то есть это развёрнутый профиль наравне с .claude/ и воссоздаётся bootstrap-ом.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Навык - это то, чем агент узнаёт процедуру проекта: /start, /task, /verify. Хост без навыков получает только AGENTS.md, то есть правила без процедур, и первое же действие делает по-своему.

## Acceptance Criteria

AC-1 После bootstrap --ide codex каталог .codex/skills/ содержит те же активные навыки, что получает claude-профиль: сравнение по ИМЕНАМ, а не по числу. AC-2 Каждый доставленный навык несёт SKILL.md - файл, по которому хост его и находит. AC-3 IDE-оверлей codex применён: тест берёт навык, у которого есть variants/ide/codex.md, и проверяет, что доставленная копия несёт содержимое оверлея, а не общий текст. AC-4 НЕГАТИВ: повторный прогон не плодит копий и не оставляет навыков, снятых с активных - удалённый из набора навык исчезает из .codex/skills/. AC-5 Существующие .codex/agents не затираются генератором навыков.

## Plan

## Rollback

Раскладка навыков в .codex/skills; откат - git revert. Каталог в .gitignore и воссоздаётся bootstrap-ом, поэтому откат ничего не разрушает.

## Journal

- 2026-09-09T16:19:54Z [planning] — ЗАМЕР ПОСЛЕ СМЕНЫ #241 СОКРАЩАЕТ ЗАДАЧУ: bootstrap --ide codex уже раскладывает навыки — в .codex/skills/ их 14, каждый несёт SKILL.md. Делает это ОБЩИЙ шаг копирования профиля, а не отдельный генератор, поэтому строить нечего. Осталось ровно то, что не проверено: применяется ли IDE-оверлей variants/ide/codex.md, и закрепление тестом (AC-1..AC-5 остаются в силе как проверка, а не как постройка).
