---
slug: next-version-reads-the-journal-tip-not-its-history
title: "next-version reads the journal tip not its history, so a write from main re-issues v1"
status: planning
epic: release-19-renar-conformance
story: renar-contract-contour
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

ЗАМЕР ПОДТВЕРЖДЁН НА ЭТОМ РЕПОЗИТОРИИ: git show main:RENAR-CONFORMANCE.yaml даёт fatal: path RENAR-CONFORMANCE.yaml exists on disk, but not in main. Артефакт живёт только на ветке v1-9-wave.

СЛЕДСТВИЕ. next_version в scripts/project_cli_renar.py берёт максимум из ДВУХ точек: файл рабочей копии и ВЕРХУШКА журнала (HEAD). История файла не читается. Значит любое состояние, где HEAD манифеста не несёт, а история несёт, ОПУСКАЕТ пол счётчика: --write с main выдаст manifest-version 1 при уже существующем v1 в коммите 42a02329, то есть ПЕРЕИСПОЛЬЗУЕТ номер с другим содержимым. §13.4.1 запрещает именно это. Тот же эффект даёт revert коммита, добавившего артефакт, и переключение на ветку старше артефакта.

ПОБОЧНОЕ СЛЕДСТВИЕ ДЛЯ ОХРАНЫ. test_the_committed_manifest_chain_resolves сверяет пару (версия, id) со МНОЖЕСТВОМ пар из истории. Если номер переиспользован с другим id, ключ id@версия перестаёт быть уникальным, и охрана примет неоднозначное совпадение как разрешение.

ПОЧЕМУ ОТДЕЛЬНОЙ ЗАДАЧЕЙ, А НЕ В ПОЧИНКЕ. Форма починки есть ВЫБОР, а не деталь: (а) максимум по всей истории файла, то есть git log по пути плюс show на каждый коммит, что делает чтение журнала O(n) вместо двух вызовов; (б) хранить отметку высшей воды отдельно; (в) читать историю только когда HEAD манифеста не несёт. Вариант меняет стоимость команды и требует замера, а не мнения.

СЕЙЧАС СДЕЛАНО ТОЛЬКО ОДНО: докстринг next_version перестал обещать one past the highest ever issued и называет остаток риска прямо, со ссылкой на эту задачу. Переобещание убрано, дефект остался.

НАЙДЕНО АДВЕРСАРИАЛЬНЫМ РЕВЬЮ (критик) на починку git-show-worktree.

## Acceptance Criteria

## Plan

## Rollback

## Journal
