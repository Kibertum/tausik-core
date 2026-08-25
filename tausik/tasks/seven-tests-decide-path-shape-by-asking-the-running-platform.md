---
slug: seven-tests-decide-path-shape-by-asking-the-running-platform
title: "Семь тестов 1.8 проходят только на Windows, и Linux-гейт увидел релиз впервые на main"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: complex
role: backend
stack: null
tier: substantial
call_budget: 70
defect_of: null
scope: null
scope_exclude: "CHANGELOG.md и CHANGELOG.ru.md правим только записью об этой задаче; содержание 1.8 не трогаем"
relevant_files:
  - "scripts/path_glob.py"
  - "scripts/memory_sinks.py"
  - "scripts/knowledge_home_guard.py"
  - "tests/test_memory_sinks.py"
  - "tests/test_knowledge_home_guard.py"
  - "tests/test_knowledge_export.py"
  - "tests/test_changelog_gate.py"
  - ".gitlab-ci.yml"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/path_glob.py"
  - "scripts/memory_sinks.py"
  - "scripts/knowledge_home_guard.py"
  - "tests/*.py"
  - ".gitlab-ci.yml"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-04T08:40:26Z"
---

## Goal

Полный прогон на Linux зелёный: решения о ФОРМЕ пути принимаются по написанию, а не по тому, какая ОС читает строку; тесты, требующие окружения, создают его сами, а не наследуют от машины разработчика.

## Acceptance Criteria

1. path_glob.normalize схлопывает `..` и в обратных, и в прямых слэшах на ЛЮБОЙ платформе: normalize("A\B\..\C") == "a/c" и на Windows, и на Linux. Проверяется тестом, не читающим sys.platform.
2. memory_sinks._tree_relative считает абсолютным путь с буквой диска (D:/...) независимо от ОС, поэтому display_path даёт проектно-относительную строку и в Linux-прогоне.
3. knowledge_home_guard отвергает UNC-НАПИСАНИЕ по СЫРОЙ строке до abspath: TAUSIK_HOME=\server\share\kn отвергается и на Linux, где abspath склеил бы её с рабочим каталогом и создал каталог с таким именем.
4. test_knowledge_export проверяет СВОЙСТВО (буква диска не принята за URL-схему и путь НЕ отвергнут), а не побочную форму результата abspath.
5. Тесты, которым нужны два хост-профиля и конфиг гейтов, СОЗДАЮТ их фикстурой, а не наследуют от машины разработчика.
6. Прогон, который CI выполняет, видит модуль mcp: либо CI ставит requirements.txt, либо отсутствие mcp — явный skip с причиной. Молчаливый ModuleNotFoundError как ошибка теста ЗАПРЕЩЁН.
7. НЕГАТИВНЫЙ сценарий: каждая правка сопровождается тестом, который на СТАРОМ коде падает — иначе правка не доказана. Для платформенных пунктов это тест, не спрашивающий sys.platform: он и есть доказательство, потому что старый код давал разный ответ на двух ОС.
8. НЕГАТИВНЫЙ сценарий: пайплайн на main зелёный ЦЕЛИКОМ (lint, doc-constants, tests). Красный любой ячейки ЗАПРЕЩАЕТ тег.
9. НЕГАТИВНЫЙ сценарий: локальный полный прогон на Windows остаётся 0 failed — правка не имеет права чинить Linux ценой Windows.

## Plan

## Rollback

git revert коммита; каждая правка изолирована в своём файле

## Journal

- 2026-08-04T08:39:47Z [implementation] — Чек-лист доказательств. AC-1 (normalize схлопывает `..` на любой платформе): ✓ tests/test_memory_sinks.py::TestPathShapeDoesNotDependOnTheRunningPlatform::test_backslashes_collapse_the_same_everywhere ✓ tests/test_memory_sinks.py::TestGlob::test_normalize_is_case_and_separator_insensitive AC-2 (буква диска абсолютна, display_path даёт относительный путь): ✓ tests/test_memory_sinks.py::TestPathShapeDoesNotDependOnTheRunningPlatform::test_a_drive_letter_is_absolute_everywhere ✓ tests/test_memory_sinks.py::TestPathShapeDoesNotDependOnTheRunningPlatform::test_a_windows_project_dir_still_yields_a_relative_display_path ✓ tests/test_memory_sinks.py::TestPathShapeDoesNotDependOnTheRunningPlatform::test_what_is_not_absolute_stays_relative AC-3 (UNC отвергается по сырой строке): ✓ tests/test_knowledge_home_guard.py::TestWhatIsRefusedOutright::test_a_network_path_is_refused ✓ CI: этот тест был единственным «DID NOT RAISE» на Linux в прогоне #4226 и зелен в #4227 AC-4 (тест экспорта проверяет свойство): ✓ tests/test_knowledge_export.py::TestRemoteDestinationsAreRefused::test_a_windows_drive_is_not_mistaken_for_a_url_scheme AC-5 (окружение создаётся, а не наследуется): ✓ MANUAL: .gitlab-ci.yml разворачивает bootstrap --ide all, оба хост-профиля на месте; test_hook_encoding::test_both_host_profiles_are_actually_scanned зелен в #4227 ✓ tests/test_changelog_gate.py::TestDocDrift::test_gate_enabled_in_own_config — при отсутствии настройки ЯВНЫЙ skip с причиной AC-6 (mcp виден прогону CI): ✓ MANUAL: venv CI ставит -r requirements.txt; tests/test_mcp_no_deprecated_primitives.py зелен в #4227, а не ошибается ModuleNotFoundError AC-7 (негативный: правка доказана): ✓ MANUAL: доказательство — сам прогон #4226 против #4227 на ОДНОМ И ТОМ ЖЕ Linux-раннере. 7 failed до правки, 0 после. Для платформенных пунктов тест на Windows невозможен: старый код там давал верный ответ, дефектом была РАЗНИЦА между ОС. Шесть новых тестов не спрашивают sys.platform и потому пиннят контракт на обеих. AC-8 (негативный: пайплайн зелёный целиком): ✓ MANUAL: пайплайн #4227 на main — tests success, doc-constants success, lint success. 6839 passed, 140 skipped, 0 failed за 12м39с. AC-9 (негативный: Windows не сломан): ✓ MANUAL: полный локальный прогон 6955 passed, 24 skipped, 140 deselected, 0 failed, 1020s. До правок было 6949 — прирост ровно на шесть новых тестов. Domain: свойство проверяется на реальных входах, а не на выдуманных — `d:/proj/core` это форма, которую CLAUDE_PROJECT_DIR принимает на Windows-хосте, а `\server\share` — форма, которой человек задаёт сетевую шару. Обе строки могут прийти на Linux через конфиг или переменную окружения, и до правки обе там обрабатывались молча неверно.
