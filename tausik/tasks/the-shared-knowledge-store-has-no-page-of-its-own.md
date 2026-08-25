---
slug: the-shared-knowledge-store-has-no-page-of-its-own
title: "У главной фичи 1.8 нет своей страницы: общая база знаний описана только внутри страницы про Notion"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: tech-writer
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: "scripts/** — документируется существующее поведение, код не трогаем"
relevant_files:
  - "docs/ru/knowledge-store.md"
  - "docs/en/knowledge-store.md"
  - "docs/ru/shared-brain.md"
  - "docs/en/shared-brain.md"
  - "docs/ru/whats-new-1.8.md"
  - "docs/en/whats-new-1.8.md"
  - README.md
  - README.ru.md
  - "scripts/docs_lint.py"
  - "scripts/audit_stale_docs.py"
scope_paths:
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - README.md
  - README.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-04T13:39:27Z"
---

## Goal

У общей базы знаний есть своя страница на двух языках, которая отвечает на два вопроса: как она работает и чем отличается от проектной базы — с таблицей «что куда класть» и с тем, чего она намеренно НЕ делает.

## Acceptance Criteria

1. Есть docs/ru/knowledge-store.md и docs/en/knowledge-store.md, зеркальные друг другу, и они описывают ЛОКАЛЬНОЕ общее хранилище ~/.tausik-knowledge/knowledge.db, а не Notion-brain.
2. На странице есть таблица различий «проектная база против общей»: что хранит, кто читает, что видно снаружи, что переживает удаление проекта, редактируется ли содержимое.
3. Названо правило, что куда класть, в проверяемой формулировке: факт об ЭТОМ проекте — в проектную, утверждение, верное в ЛЮБОМ проекте, — в общую; и приведены примеры обеих ошибок.
4. Перечислено, чего хранилище НАМЕРЕННО не делает: не редактирует содержимое, не уезжает с машины, не синхронизируется, не является Notion-brain; и сказано, как это связано с проверкой TAUSIK_HOME.
5. Описаны команды целиком: memory add --global, поиск по обоим хранилищам, knowledge export, knowledge restore, knowledge import-brain, и что делает doctor.
6. Обе страницы связаны взаимными ссылками с shared-brain.md, whats-new-1.8.md и README; audit_stale_docs остаётся зелёным — страница, на которую никто не ссылается, считается протухшей.
7. НЕГАТИВНЫЙ сценарий: страница НЕ повторяет содержимое shared-brain.md, а разграничивает — читатель после неё способен ответить, куда попадёт запись при --global и почему это НЕ Notion.
8. НЕГАТИВНЫЙ сценарий: docs_lint и audit_stale_docs зелёные; сломанная ссылка или несимметричное зеркало ЗАПРЕЩЕНЫ.

## Plan

## Rollback

git revert коммита; новые файлы удаляются, ссылки из индекса снимаются

## Journal

- 2026-08-04T13:37:54Z [implementation] — Чек-лист доказательств. AC-1 (две зеркальные страницы про ЛОКАЛЬНОЕ хранилище): ✓ MANUAL: docs/ru/knowledge-store.md и docs/en/knowledge-store.md созданы, предмет — ~/.tausik-knowledge/knowledge.db; Notion-brain явно отведён в отдельную страницу первым же абзацем AC-2 (таблица различий): ✓ MANUAL: девять строк — где лежит, сколько их, что хранит, что переживает, кто читает, едет ли в git, редактируется ли содержимое, видно ли снаружи, есть ли бэкап AC-3 (правило что куда, с примерами обеих ошибок): ✓ MANUAL: формулировка «факт об ЭТОМ проекте — в проектную, утверждение, верное в ЛЮБОМ — в общую», проверка «прочитайте это через полгода в другом репозитории», плюс ошибка первого рода (проектное в общее) и второго (общее в проектном), обе с кодом AC-4 (чего НАМЕРЕННО не делает): ✓ MANUAL: пять пунктов — не редактирует, не покидает машину (со связью с проверкой TAUSIK_HOME), не синхронизируется, не помнит заказчика, не является Notion-brain AC-5 (команды целиком): ✓ MANUAL: memory add --global, search по обоим, knowledge export, knowledge restore, knowledge import-brain, doctor — сверено с `tausik knowledge --help`, лишних команд не выдумано AC-6 (взаимные ссылки, страница не протухшая): ✓ MANUAL: docs_lint clean, audit_stale_docs «No stale docs detected. (OK)» — страница, на которую никто не ссылается, там считается протухшей, значит ссылки живут ✓ MANUAL: ссылки проставлены из whats-new (обе), shared-brain (обе) и README (оба) AC-7 (негативный: не дублирует shared-brain, а разграничивает): ✓ MANUAL: в shared-brain обоих языков вставлена врезка «это не та страница», а в knowledge-store — таблица трёх хранилищ с колонкой «уезжает наружу»: только Notion — да AC-8 (негативный: гейты зелёные): ✓ MANUAL: docs_lint clean, audit_stale_docs OK, 76 тестов доковой группы зелёные Domain: проверяется тем, способен ли читатель после страницы ответить на вопрос «куда попадёт запись при --global и почему это НЕ Notion». Таблица трёх хранилищ отвечает на него одной строкой, а раздел «чего не делает» объясняет, почему у локального общего нет скраббера, а у Notion есть.
