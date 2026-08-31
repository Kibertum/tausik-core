---
slug: db-gated-ratchets-never-run-in-ci
title: "Храповики, стоящие под опубликованными утверждениями манифеста, в CI не выполняются: базы проекта там нет"
status: planning
epic: release-19-renar-conformance
story: test-evidence-not-test-volume
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

НАЙДЕНО СВЕРКОЙ SENAR 9.5 В #202 ДВУМЯ НЕЗАВИСИМЫМИ АГЕНТАМИ, ПОДТВЕРЖДЕНО ЗАМЕРОМ.

ЧТО ИЗМЕРЕНО. git check-ignore показывает .gitignore:25 на .tausik/, git ls-files .tausik пуст, grep по .github/workflows/ не находит ни tausik.db, ни tausik init: единственный шаг подготовки есть bootstrap.py, который базу не создаёт. Значит все тесты, начинающиеся с проверки наличия .tausik/tausik.db, в CI ТИХО ПРОПУСКАЮТСЯ.

КАКИЕ ИМЕННО ЗАЩИТЫ ЭТО ЗАТРАГИВАЕТ, И ПОЧЕМУ ЭТО НЕ МЕЛОЧЬ. (1) test_adr_013_conditional_obligations_are_still_vacuous — ЕДИНСТВЕННЫЙ потребитель classes_appeared, то есть машина, гасящая объявление ADR-013. Манифест ПРЯМО НАЗЫВАЕТ её в строке evidence как основание, по которому опубликованное true безопасно. (2) test_the_task_that_emptied_the_registry_is_real_and_underway — встречный храповик REGISTRY_EMPTIED_BY, без которого опустошение реестра оговорок есть однострочное удаление, читающееся как «незаслуженных подтверждений нет».

ОБЕ ЗАЩИТЫ СЕГОДНЯ ЖИВУТ ТОЛЬКО НА МАШИНЕ РАЗРАБОТЧИКА С ОСТАТОЧНЫМ СОСТОЯНИЕМ. Детектор, который не может ВЫПОЛНИТЬСЯ в среде, где стоит гейт, заслуживает того же разбора, что и детектор, который не может покраснеть, — а релиз именно про вторых.

НАПРАВЛЕНИЯ, ВЫБОР ВНУТРИ ЗАДАЧИ И ПО ЗАМЕРУ. (а) создавать в CI схемную базу перед лентой; (б) перенести проверку с SQLite на git-отслеживаемую проекцию tausik/, которая для того и коммитится — .gitignore прямо говорит, что durable projection живёт в НЕдотовом tausik/; (в) как минимум сделать пропуск ГРОМКИМ при переменной CI, чтобы разрыв был виден отчётом, а не прятался в двадцати шести skipped. Вариант (б) выглядит сильнейшим: он снимает зависимость от остаточного состояния вообще, но требует проверить, что проекция содержит нужные строки.

## Acceptance Criteria

## Plan

## Rollback

git revert коммита задачи. Если решением станет создание схемной БД в CI — удалить шаг из workflow; данных задача не трогает.

## Journal
