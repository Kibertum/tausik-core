---
slug: write-gate-resolves-relative-paths-against-the-wrong-directory
title: "Гейт записи резолвит относительные пути от каталога проекта, а не от рабочего каталога команды: работа в чужой выгрузке блокируется"
status: planning
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: write-gate-parses-command-text-not-writes
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО ЖИВЬЁМ В #204 ПРИ ПРОВЕРКЕ «РАБОТАЕТ ЛИ ИЗ ЧИСТОГО КЛОНА». Гейт заблокировал обычную команду уборки в git worktree, объявив целью записи путь В ГЛАВНОМ репозитории.

ЗАМЕР, ВОСПРОИЗВОДИМЫЙ ОДНОЙ КОМАНДОЙ. После `cd D:/tmp/tausik-bare-204` команда `rm -f .tausik/tausik.db*` даёт exit 2 с текстом «writes outside the active task's declared scope: .tausik/tausik.db*». Никакого файла в главном репозитории команда не трогает — она работает в ДРУГОЙ выгрузке.

КОРНЕВАЯ ПРИЧИНА, И ОНА НАЗВАНА В САМОМ КОДЕ. scripts/hooks/bash_write_gate.py: «A Bash redirect/target is relative to the shell's cwd — the project dir — not to wherever this hook process happened to launch», и далее cand = os.path.join(project_dir, expanded). Отождествление «cwd оболочки == project_dir» верно для обычной работы и НЕВЕРНО, как только агент делает cd в другое дерево. Хук получает событие без cwd, поэтому берёт единственное, что у него есть.

ПОЧЕМУ ЭТО ВАЖНО ИМЕННО СЕЙЧАС. Владелец подтвердил решением #299, что «работает у чужого из чистого клона» входит в требования 1.9. Единственный честный способ это проверить — git worktree (память #501). То есть гейт мешает ровно той проверке, которая теперь обязательна: обход существует (абсолютные пути), но его надо ЗНАТЬ, и он найден ценой заблокированной команды.

НАПРАВЛЕНИЕ ОШИБКИ. Это ЛОЖНЫЙ БЛОК, а не дыра: чужое дерево ошибочно считается своим, то есть гейт пере-обнаруживает. Чинить, не превратив в под-обнаружение: путь в ДРУГОМ дереве не должен молча становиться разрешённым.

ЧТО ВЫЯСНИТЬ ПЕРВЫМ ДЕЛОМ, ДО ПРОЕКТИРОВАНИЯ. Несёт ли событие хука фактический рабочий каталог (поле cwd в payload PreToolUse) — если да, задача сводится к тому, чтобы его читать; если нет, решать по-другому (например, не считать целью путь, чей резолв не существует ни как файл, ни как каталог-родитель). НЕ УГАДЫВАТЬ: прочитать реальный payload, как велит урок #203 — конфиг именно той системы, о которой утверждаешь.

ИНВЕНТАРЬ ДО ОЦЕНКИ: проверить ОБА канала (bash_write_gate и pwsh), и оба гейта (scope-ACL и QG-0 task_gate), а не только тот, что ударил.

## Acceptance Criteria

## Plan

## Rollback

## Journal
