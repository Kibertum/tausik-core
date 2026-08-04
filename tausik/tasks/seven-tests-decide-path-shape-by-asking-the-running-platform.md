---
slug: seven-tests-decide-path-shape-by-asking-the-running-platform
title: "Семь тестов 1.8 проходят только на Windows, и Linux-гейт увидел релиз впервые на main"
status: active
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
completed_at: null
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
