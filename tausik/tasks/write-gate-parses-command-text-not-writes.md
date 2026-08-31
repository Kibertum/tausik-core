---
slug: write-gate-parses-command-text-not-writes
title: "Гейт записи разбирает текст команды: запись из скрипта уходит мимо ACL задачи"
status: planning
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
role: developer
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
---

## Goal

bash_write_gate решает, какие пути запишет команда, РАЗБИРАЯ ЕЁ ТЕКСТ. Запись, выполненная ВНУТРИ вызванного скрипта, в тексте не видна и через ACL задачи проходит насквозь. Замерено живьём в #200: `cp /tmp/x .claude/mcp/project/tools_spec.py` ОТКЛОНЁН гейтом с перечислением ACL, а `python /tmp/edit2.py`, открывающий ровно тот же путь на запись, прошёл и правку записал — при том что .claude/ в ACL задачи не было и правка .claude/ напрямую запрещена CLAUDE.md. Тот же класс покрывает любой `python bootstrap/bootstrap.py` и любой хелпер-скрипт. ЦЕНА: текст отказа утверждает «this Bash command writes outside the active task's declared scope», то есть заявляет проверку ЗАПИСЕЙ, а проверяет ИМЕНА В СТРОКЕ. Это вырожденность по ADR-021 в формулировке, а не в коде: гейт делает меньше, чем говорит, и агент, прочитавший отказ, считает ACL закрытым. ВОЗМОЖНЫЕ ПУТИ (решить в задаче, не предрешать здесь): (1) сузить ОБЕЩАНИЕ — переписать текст отказа и документацию так, чтобы гарантия называлась честно, и это дёшево; (2) закрыть дыру по-настоящему — сверять git status ДО и ПОСЛЕ каждой команды и краснеть на записи вне ACL, что ловит любой путь исполнения, но платит временем на каждом вызове; (3) гибрид — честный текст плюс пост-проверка только для команд, запускающих интерпретатор. НЕГАТИВНЫЙ СЦЕНАРИЙ ДЛЯ AC: скрипт, пишущий файл вне ACL, ОБЯЗАН быть пойман; сегодня он не ловится, и тест на это обязан краснеть до починки.

## Acceptance Criteria

## Plan

## Rollback

## Journal
