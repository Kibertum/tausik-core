---
slug: qwen-hooks-are-a-second-copy-of-the-declaration
title: "Профиль qwen строит хуки своим списком вместо общего объявления — разойдётся молча и не сразу"
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

ЗАМЕР, смена #241, найдено при подключении Codex. Набор хуков объявлен один раз в bootstrap_hooks.build_hooks_dict и параметризован тем, КАК строится строка команды. Профиль claude им пользуется (bootstrap_generate.py:62), новый профиль codex тоже. Профиль qwen - НЕТ: bootstrap_qwen.py строит собственный список, повторяя имена скриптов вручную (task_gate.py, scope_write_gate.py, read_ledger_gate.py, memory_pretool_block.py, secret_scan.py, bash_firewall.py и далее по строкам 99-160).

ПОЧЕМУ ЭТО ДЕФЕКТ, А НЕ СТИЛЬ. Хук, добавленный в общее объявление, у qwen молча не появится. Расхождение не проявится сразу: оно проявится через несколько релизов и на чужой машине, где гейт, объявленный обязательным, просто не сработает. Ровно этот класс только что стоил Codex тринадцати мёртвых гейтов, и ровно против него написан AC-5 задачи codex-bootstrap-writes-hooks-that-actually-fire - но у qwen такой охраны нет.

СВЕРИТЬ ПЕРЕД ПРАВКОЙ: списки могут уже РАСХОДИТЬСЯ. Первый шаг - замер, какие хуки есть у claude и отсутствуют у qwen; если расхождение есть, оно и есть находка, а унификация - её починка.

## Acceptance Criteria

AC-1 ЗАМЕР ПЕРВЫМ: названо, какие хуки есть у claude и отсутствуют у qwen на момент правки - число и имена, а не 'расхождений нет'. AC-2 qwen строит набор из build_hooks_dict, как claude и codex. AC-3 Способ построения команды у qwen остаётся СВОИМ - унифицируется набор, а не путь. AC-4 НЕГАТИВ: тест краснеет, если у любого из трёх хостов набор событий или матчеров разошёлся с общим объявлением - той же формы, что TestНаборОдинНаДваХоста у codex, но на все три.

## Plan

## Rollback

Замена собственного списка qwen на общее объявление; откат - git revert. Развёрнутые профили пересоздаются bootstrap-ом, поэтому откат не оставляет мусора.

## Journal
