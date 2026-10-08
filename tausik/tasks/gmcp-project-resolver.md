---
slug: gmcp-project-resolver
title: "[P0] resolve_project(): цепочка не-депрекированный механизм -> pointer -> cwd/env"
status: done
epic: v2-global-mcp
story: v2gm-core
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Изолированный модуль resolve_project: цепочка primary -> pointer -> walk-up, без БД и сети. Подъём НЕ переписывается второй раз: find_tausik_dir разделяется на чистую функцию от (cwd, env) и тонкую обёртку, иначе в проекте появятся два ответа на вопрос «где проект»."
scope_exclude: null
relevant_files:
  - "scripts/gmcp_project_resolver.py"
  - "tests/test_gmcp_project_resolver.py"
  - "scripts/project_config.py"
scope_paths:
  - "scripts/gmcp_project_resolver.py"
  - "tests/test_gmcp_project_resolver.py"
  - "scripts/project_config.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-28T22:07:58Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#35"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ПОРЯДОК ЦЕПОЧКИ ИЗМЕНЁН в сессии #121 задачей l26-roots-premise-fix.  БЫЛО: roots -> pointer -> cwd/env. Roots стояли ПЕРВЫМ звеном. СТАЛО: механизм, выбранный спайком из не-депрекированных (параметр тула / resource URI / конфиг сервера) -> глобальный active-pointer ~/.tausik/active-project.json (ключ по session/pid) -> cwd/TAUSIK_DIR walk-up (есть find_tausik_dir).  ПРИЧИНА. Спека MCP от 2026-07-28 депрекирует roots (SEP-2577). Строить первое звено цепочки резолва на депрекированном примитиве значит закладывать переделку в фундамент. Депрекация annotation-only с гарантией не менее 12 месяцев — срочности нет, поэтому правка сделана сейчас текстом, а не потом кодом. Мигрировать при этом нечего: аудит l26-mcp-deprecation-audit замерил 0 обращений к депрекируемому API на 19 файлах MCP-треда.  ROOTS НЕ ВЫЧЕРКНУТЫ. Если спайк gmcp-spike-roots обнаружит, что хост не поддерживает ни один из не-депрекированных механизмов, roots остаются первым звеном как ПЕРЕХОДНЫЙ путь на гарантированный срок. Модуль обязан быть написан так, чтобы источник первого звена был параметром, а не зашитым решением, — тогда смена механизма не переписывает цепочку.  Модуль изолированный: возвращает project_dir или None; не лезет в БД и в сеть.

## Acceptance Criteria

1. resolve_project(primary_signal, env, cwd) детерминирован и покрыт unit-тестами на КАЖДУЮ ветку приоритета. Первое звено передаётся параметром, а не читается изнутри: механизм выбирает спайк, и модуль не должен переписываться при его смене.
2. НЕГАТИВНЫЙ: ни одного сигнала (нет первичного, нет pointer, cwd вне TAUSIK-проекта) -> None без исключения.
3. НЕГАТИВНЫЙ: битый active-pointer JSON -> ветка пропускается с логом, без краша. Пустой файл, невалидный JSON и валидный JSON без нужного ключа проверяются по отдельности — это три разных отказа, и сводить их в один тест значит не проверить два.
4. НЕГАТИВНЫЙ: pointer указывает на несуществующий каталог -> ветка пропускается, а не возвращает мёртвый путь. Мёртвый project_dir хуже None: вызывающий примет его за рабочий.
5. pytest: приоритет primary > pointer > cwd, None-случай, все три формы битого pointer, мёртвый путь.
6. Переходный путь не забыт: если спайк оставил roots первичным, это проходит тем же параметром primary_signal и НЕ требует правки модуля. Проверяется тестом, подающим roots-подобное значение.

## Plan

## Rollback

git revert. Новый модуль никто ещё не вызывает — подключение делает следующая задача цепочки, поэтому откат не меняет поведения ни одной команды. Разделение find_tausik_dir на чистую часть и обёртку поведение сохраняет, что закрепляют существующие тесты на подъём.

## Journal

- 2026-09-28T21:54:25Z [implementation] — AC-1: ✓ tests/test_gmcp_project_resolver.py::TestThePriorityOrder — четыре теста, включая один, где ТОТ ЖЕ cwd резолвится по-разному по мере добавления ранних звеньев. Первое звено — параметр primary_signal, читается не изнутри. AC-2: ✓ ::TestNoSignalIsNoneAndNotAnException — None без исключения; отсутствие указателя НЕ помечается как отказ, иначе шум на каждом вызове. AC-3: ✓ ::TestThePointerFailsInThreeDistinctWays — пустой файл, невалидный JSON, валидный без ключа, плюс валидный не-объект: четыре различимые причины, четыре теста, ни один не бросает.
- 2026-09-28T21:54:26Z [implementation] — AC-4: ✓ ::TestADeadPathIsWorseThanNone — указатель на исчезнувший каталог и каталог без .tausik пропускаются с записанной причиной, мёртвый путь не возвращается. AC-5: ✓ 33 теста в файле, все ветки приоритета покрыты. AC-6: ✓ ::TestTheTransitionalRootsPathNeedsNoChange — file:// URI проходит тем же параметром; проверены percent-encoding и отказ от URI, называющего другую машину. ПОБОЧНО: подъём НЕ написан второй раз — find_tausik_dir разделён на чистую tausik_dir_from(cwd, env) и обёртку, резолвер зовёт чистую; ::test_the_walk_up_is_the_project_s_only_one держит это. Указатель в тире 1.10, а не в ~/.tausik.
- 2026-09-28T22:03:57Z [implementation] — NO-DEAD-END: красный прогон — не про модуль, а про два гейта репозитория, и оба закрыты по существу. (1) bootstrap_drift: 12 развёрнутых файлов разошлись с исходником, потому что редеплой профилей я сделал ДО последней правки — конвенция #754, отработала как задумано. (2) test_dedupe: два теста из четырёх, которых требует AC-3, вышли структурно неразличимыми. Сводить их в один нельзя — критерий прямо запрещает, — поэтому каждый получил утверждение, которое может сделать только он: пустой файл проверяется тремя формами пустоты, невалидный JSON обязан назвать НОМЕР СТРОКИ, потому что указатель правят руками. Это не обход храповика, а то, чего ему не хватало.
