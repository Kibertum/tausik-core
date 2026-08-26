---
slug: output-discipline-reaches-the-agent-once-not-every-turn
title: "Директива экономии вывода доезжает до агента ОДИН раз при bootstrap, в preserve-if-exists файл, а не на каждом ходу"
status: planning
epic: landscape-2026-h2
story: agent-output-discipline
complexity: null
role: architect
stack: python
tier: moderate
call_budget: 40
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

ИСТОЧНИК: github.com/ayghri/i-have-adhd (MIT), сессия #185. Его несущая часть — не SKILL.md, а hooks/always-on.{mjs,sh,ps1} + hooks/hooks.json: правила впрыскиваются КАЖДЫЙ ход, а не лежат в файле, который мог быть прочитан однажды.

НАШ МЕХАНИЗМ УСТРОЕН ИНАЧЕ, И ЭТО НАДО ЗАМЕРИТЬ ВЫЗОВОМ, А НЕ ПРОЧЕСТЬ ГЛАЗАМИ. Директива output_mode: caveman добавляется в генерируемый файл правил в bootstrap/bootstrap_templates.py, а всякий генератор правил — preserve-if-exists. Там же живёт warn_output_mode_not_applied: продукт САМ предупреждает, что при уже существующем файле правил запрошенный режим до агента не доедет. То есть путь доставки известен как хрупкий и назван в коде, но вопрос «доезжает ли директива на КАЖДОМ ходу и переживает ли она компакцию контекста» не задавался никогда.

ЗАМЕР ДО КОДА, три вопроса, на каждый — ответ вызовом:
1) где именно директива достигает агента сейчас (файл правил, SessionStart-хук, оба, ни одного) и для каких IDE из пяти зеркал;
2) переживает ли она компакцию длинной сессии — остаётся ли правило в контексте к 150-й минуте, или живёт только в начале;
3) сколько стоит впрыск на каждом ходу в байтах и окупается ли он экономией вывода. Крышка на вход не может стоить дороже того, что она экономит на выходе.

ГРАНИЦА. Не вводить второй рычаг рядом с caveman — решение уже записано в задаче response-contract-sets-a-shape-not-only-a-length: расширить существующий или заменить, но не оставить два об одном. Задача output-economy-mode-is-shipped-but-off-in-our-own-project — про то, что режим ВЫКЛЮЧЕН у нас; эта — про то, что даже включённый доезжает один раз. Не сливать их: первая закрывается сменой конфига, вторая — только после замера пути доставки.

## Acceptance Criteria

## Plan

## Rollback

## Journal
