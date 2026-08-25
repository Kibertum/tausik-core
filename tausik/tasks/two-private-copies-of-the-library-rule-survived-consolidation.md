---
slug: two-private-copies-of-the-library-rule-survived-consolidation
title: "Две частные копии правила «где библиотека» пережили сведение к library_source"
status: done
epic: arch-debt-post-18
story: adp18-module-boundaries
complexity: simple
role: backend
stack: null
tier: light
call_budget: null
defect_of: null
scope: null
scope_exclude: "bootstrap/**, harness/** — вопрос в scripts/ и документации"
relevant_files:
  - "scripts/service_doctor_drift.py"
  - "scripts/skill_deps.py"
  - "tests/test_consumer_layout.py"
  - "docs/ru/hooks.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/**"
  - "tests/*.py"
  - "docs/**"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-12T20:28:32Z"
---

## Goal

Вопрос «где библиотека» задаётся одной функции. Копий с обратным приоритетом не остаётся.

## Acceptance Criteria

1. service_doctor_drift.claudemd_drift_report (строки 98-99) разрешает библиотеку через library_source. Сейчас там два подряд sys.path.insert(0, ...), и второй — путь ПРОЕКТА — побеждает, то есть приоритет обратен правилу «библиотека побеждает», установленному тем же коммитом тремя строками выше в соседней функции того же файла. Проверки os.path.isdir нет.
2. skill_deps._resolve_venv_python (строка 35) разрешает библиотеку через тот же library_source: его список кандидатов проверяет проектные пути ПЕРЕД сабмодулем — третья копия того же вопроса.
3. НЕГАТИВНЫЙ: в репозитории разработки, где project_dir == lib_dir, поведение обеих функций не меняется.
4. Регрессия закреплена на фикстуре tests/consumer_layout.py: дрейф CLAUDE.md сверяется с bootstrap_templates БИБЛИОТЕКИ, а не с одноимённым каталогом проекта. Сейчас claudemd_drift_report на потребительской фикстуре не проверяется вовсе.
5. docs/ru/hooks.md:79 перестаёт учить потребителя команде git config core.hooksPath scripts/hooks: в потребительской раскладке этот каталог принадлежит проекту и pre-commit там нет, а git считает отсутствующий хук не ошибкой, а отсутствием — установка молча не срабатывает.

## Plan

## Rollback

git revert

## Journal

- 2026-08-12T20:28:30Z [implementation] — AC-1 (claudemd_drift_report через library_source): ✓ scripts/service_doctor_drift.py — своё вычисление с двумя sys.path.insert(0, …) подряд, где второй (путь проекта) оказывался первым, заменено на общую функцию. ✓ tests/test_consumer_layout.py::test_claudemd_drift_asks_the_shared_resolver_for_the_library. AC-2 (skill_deps._resolve_venv_python через library_source): ✓ library_source стоит ПЕРВЫМ кандидатом; относительные __file__-кандидаты оставлены осознанно и это объяснено в докстринге — они отвечают на другой вопрос («лежит ли скрипт внутри чекаута движка»), на который функция, считающая от каталога проекта, ответить не может. AC-3 (НЕГАТИВНЫЙ: в репозитории разработки поведение не меняется): ✓ полный прогон 7002 passed, 0 failed — включая 13 проверок test_doctor_drift_baselines, которые РАННЯЯ версия этой же правки погасила: ранний return None при отсутствии каталога был неверен, потому что bootstrap_templates бывает уже доступен по пути. Ошибка поймана прогоном, исправлена, причина записана в самом коде. AC-4 (регрессия на фикстуре consumer_layout): ✓ закреплён ВЫЗОВ, а не результат, и это осознанно: результат обеих редакций на фикстуре совпадает, тест на результат был бы зелёным до починки. Проверено обратным прогоном на git stash — тест краснеет на откате и зеленеет на правке (конвенция #365). AC-5 (docs/ru/hooks.md): ✓ раздел установки разделён на репозиторий TAUSIK и потребительский проект; названо, что git считает отсутствующий хук не ошибкой, а отсутствием, и потому прежняя команда молча не срабатывала; добавлена git submodule update --init. Domain: три копии правила отвечали на один вопрос «где библиотека» и расходились в приоритете — этого достаточно, чтобы doctor у потребителя считал дрейф по чужому шаблону. Осталась одна функция. ruff чист.
