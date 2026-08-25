---
slug: py313-changed-isabs-and-the-path-redactor-stopped-redacting
title: "Python 3.13 сменил ntpath.isabs, и редактор путей на Windows перестал редактировать"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: backend
stack: null
tier: light
call_budget: 25
defect_of: seven-tests-decide-path-shape-by-asking-the-running-platform
scope: null
scope_exclude: ".github/**, .gitlab-ci.yml — окружение ни при чём"
relevant_files:
  - "scripts/knowledge_origin.py"
  - "tests/test_knowledge_origin.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/knowledge_origin.py"
  - "tests/test_knowledge_origin.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-04T11:33:27Z"
---

## Goal

relative_source_file решает абсолютность по НАПИСАНИЮ, как уже решает соседний код того же модуля, и потому не зависит ни от ОС, ни от версии Python.

## Acceptance Criteria

1. relative_source_file определяет абсолютность через _ABSOLUTE_RE — предикат, который ЭТОТ ЖЕ модуль уже завёл и в комментарии прямо написал, что os.path.isabs использовать нельзя.
2. Путь вида \work\clients\acme\repo\scripts\a.py становится относительным на ЛЮБОЙ платформе и на любой версии Python; проверяется тестом, не спрашивающим sys.platform и sys.version_info.
3. test (windows-latest, 3.13) на PR релиза зелёный.
4. НЕГАТИВНЫЙ сценарий: путь ВНЕ проекта по-прежнему сводится к basename, а не к цепочке ../.. — редактирование не должно ослабнуть ради того, чтобы тест позеленел. Пиннится существующими проверками на отсутствие '..' и 'bravo' в результате.
5. НЕГАТИВНЫЙ сценарий: уже относительное значение возвращается неизменным; путь, который лишь СОДЕРЖИТ разделитель (team/backend), абсолютным не считается и не портится.

## Plan

## Rollback

git revert коммита; правка в одной функции

## Journal

- 2026-08-04T11:32:15Z [implementation] — Чек-лист доказательств. AC-1 (предикат модуля вместо os.path.isabs): ✓ MANUAL: scripts/knowledge_origin.py::relative_source_file теперь вызывает _ABSOLUTE_RE.match; os.path.isabs в функции нет AC-2 (независимость от платформы и версии): ✓ tests/test_knowledge_origin.py::TestAbsolutenessIsSpellingNotInterpreterOpinion::test_the_predicate_reads_the_spelling_on_every_platform ✓ tests/test_knowledge_origin.py::TestAbsolutenessIsSpellingNotInterpreterOpinion::test_a_rooted_path_in_this_platforms_spelling_is_redacted AC-3 (windows 3.13 зелёный): ✓ MANUAL: подтверждается прогоном PR #6 после правки AC-4 (негативный: редактирование не ослабло): ✓ tests/test_knowledge_origin.py::TestAbsolutenessIsSpellingNotInterpreterOpinion::test_a_path_outside_the_project_still_collapses_to_a_basename ✓ tests/test_knowledge_origin.py::TestSnippetSourceFiles::test_a_path_outside_the_project_does_not_climb_out_of_it AC-5 (негативный: свободный текст не портится): ✓ tests/test_knowledge_origin.py::TestAbsolutenessIsSpellingNotInterpreterOpinion::test_a_value_that_merely_contains_a_separator_is_left_alone Отдельно про форму теста. Первая редакция утверждала, что путь `\work\...\a.py` станет "scripts/a.py" на ЛЮБОЙ платформе. Это неверно: POSIX-хост не умеет разбить путь с обратными слэшами на сегменты, и честный ответ там — basename. Я чуть не внёс ровно тот дефект, который чиню, — тест, зелёный на одной ОС. Утверждение разделено на два: кросс-платформенное про ПРЕДИКАТ (там оно истинно) и сквозное в написании текущей платформы (там оно проверяемо). Domain: колонка source_file читается человеком, который смотрит общую базу знаний. Путь вида \work\clients\acme\repo\... называет заказчика. Именно это редактирование и убирает, и именно оно молча перестало работать.
- 2026-08-04T11:33:08Z [implementation] — Root cause (dependency): relative_source_file спрашивал абсолютность у os.path.isabs, чей ответ принадлежит СТОРОННЕЙ реализации и меняется между минорными версиями — Python 3.13 перестал считать абсолютным путь с одним ведущим разделителем и без буквы диска на Windows, и редактирование раскладки каталогов молча выключилось. Prevention: предикаты о ФОРМЕ входа (абсолютность, UNC, буква диска) читают написание строки регулярным выражением или собственной функцией и НЕ делегируют платформенному модулю; в этом же модуле такой предикат _ABSOLUTE_RE уже был заведён с записанным объяснением, и правило теперь соблюдают все его функции, а не все кроме одной.
