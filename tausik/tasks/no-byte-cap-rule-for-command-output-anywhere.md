---
slug: no-byte-cap-rule-for-command-output-anywhere
title: "Ни одного правила байтовой крышки на вывод команды: строчные лимиты не держат одну длинную строку"
status: planning
epic: landscape-2026-h2
story: agent-output-discipline
complexity: null
role: developer
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

Поиск по bootstrap/, harness/, scripts/ и docs/ даёт НОЛЬ упоминаний байтовых крышек (head -c, tail -c) и ноль правил о размере вывода команды. Строчные лимиты, которые агент выбирает сам, не защищают: одна длинная строка (минифицированный файл, JSON в одну строку, лог без переносов) переполняет контекст независимо от числа строк. Внешний источник, у которого этот приём измерен — github.com/Austin1serb/agents-md — называет его своим главным выигрышем и заявляет около -50% токенов на сопоставимых задачах; цифра ЧУЖАЯ и у нас не проверена, повторять её как свой результат нельзя (та же оговорка уже сделана про 65% caveman в комментарии к CAVEMAN_DIRECTIVE). Задача: ввести правило байтовой крышки для вывода неизвестного размера и назвать список команд, для которых безлимитный вызов запрещён (cat без диапазона, широкий rg, find, ls -R, git diff целиком). Проверить приёмом, который у нас уже принят для гейтов: правило проверяется мутацией, а не тем, что оно записано. Замер до и после — на нашем же наборе, а не пересказом чужого.

## Acceptance Criteria

## Plan

## Rollback

## Journal
