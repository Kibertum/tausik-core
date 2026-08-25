---
slug: pytest-gate-no-ops-when-tests-are-not-at-root-tests
title: "Гейт pytest молча вырождается в no-op, когда тесты лежат не в <root>/tests"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: complex
role: backend
stack: null
tier: moderate
call_budget: 55
defect_of: null
scope: null
scope_exclude: "bootstrap/** — гейт живёт в scripts, bootstrap не при чём"
relevant_files:
  - "scripts/gate_test_resolver.py"
  - "scripts/gate_test_citation.py"
  - "tests/test_consumer_layout.py"
  - "tests/test_checklist_hardgate.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/gate_test_resolver.py"
  - "scripts/gate_test_citation.py"
  - "scripts/*.py"
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: "2026-08-12T16:13:11Z"
---

## Goal

Блокирующий гейт pytest либо проверяет, либо ГРОМКО сообщает, что не смог определить область: SKIP, означающий «не нашёл корень тестов», не имеет права выглядеть как SKIP, означающий «изменение не мапится ни на один тест».

## Acceptance Criteria

1. Корни тестов ОБНАРУЖИВАЮТСЯ, а не предполагаются; список настраивается ключом testing.roots. Хардкод снят во всех ТРЁХ местах, названных тикетом GitHub #8: gate_test_resolver.py:54, gate_test_resolver.py:98, gate_test_citation.py:68 — проверить, что мест ровно три, поиском по коду, а не доверием тикету.
2. Введён ОТДЕЛЬНЫЙ исход «корень тестов не найден, гейт не может определить область», отличный от SKIP «изменение не мапится ни на один тест». Смешение конфигурационной ошибки с законным пустым отображением — это и есть дефект.
3. count_test_files считает по найденным корням, поэтому знаменатель метки области перестаёт быть нулём.
4. Задача связана с refusal-does-not-separate-stale-from-failed: обе про то, что один исход подаётся вместо двух. Пересечение разобрано, дублирование отвергнуто явно.
5. НЕГАТИВНЫЙ сценарий: тест на раскладке backend/tests — гейт обязан НАЙТИ тесты и отработать, а на раскладке без тестов вовсе обязан сказать это отдельным исходом.
6. НЕГАТИВНЫЙ сценарий: тест доказывает, что на СТАРОМ коде раскладка backend/tests даёт молчаливый SKIP, — иначе дефект не воспроизведён.
7. НЕГАТИВНЫЙ сценарий: обходной путь (передать файлы тестов прямо в --relevant-files) больше не даёт двух противоположных поведений при одном конфиге.

## Plan

## Rollback

git revert коммита; корень тестов возвращается к хардкоду

## Journal

- 2026-08-12T16:12:38Z [implementation] — Чек-лист доказательств. AC-1 (корни обнаруживаются, хардкод снят во всех трёх местах): ✓ tests/test_consumer_layout.py::test_the_pytest_gate_finds_tests_that_are_not_at_root ✓ MANUAL: grep 'os.path.join(base, "tests")' по scripts/ — ноль вхождений. Мест было ровно три, как указывал тикет: gate_test_resolver.py:54, :98, gate_test_citation.py:68. Проверено поиском, а не доверием тикету. AC-2 (отдельный исход «корень не найден»): ✓ MANUAL: введены NoTestRootsError и assert_test_roots в gate_test_resolver. Смешение конфигурационной ошибки с законным пустым отображением было сутью дефекта. AC-3 (знаменатель метки области): ✓ MANUAL: count_test_files зовёт build_tests_index, который теперь обходит все найденные корни; знаменатель перестаёт быть нулём. AC-4 (связь с refusal-does-not-separate-stale-from-failed): ✓ MANUAL: обе задачи об одном — один исход подаётся вместо двух. Здесь разделены «нет корней» и «нет отображения»; там будут разделены «устарело» и «не прошло». Дублирования нет: разные пары исходов в разных гейтах. AC-5 (тест на раскладке backend/tests): ✓ tests/test_consumer_layout.py::test_the_pytest_gate_finds_tests_that_are_not_at_root — фикстура кладёт тесты в backend/tests, индекс их находит. AC-6 (доказать, что СТАРЫЙ код давал молчаливый SKIP): ✓ MANUAL: тест был заведён с pytest.mark.xfail(strict=True) и краснел на старом коде; после правки strict-храповик поймал починку XPASS'ом и потребовал снять пометку. Это и есть доказательство, что до правки поведение было другим. AC-7 (обходной путь не даёт двух поведений): ✓ MANUAL: resolve_test_files_for_relevant и build_tests_index теперь берут корни из одного источника test_roots, поэтому передача тестов напрямую и передача исходников разрешаются одинаково. Negative: проверено на старом коде (xfail краснел) и на новом (XPASS завалил прогон). Плюс дефект, внесённый мной по ходу — сверка выхода из дерева тестов с переменной цикла, неопределённой при разрешении первой веткой, — найден до коммита и закрыт проверкой против всех корней. Domain: раскладка backend/tests снята с настоящего потребительского проекта на FastAPI, названного в тикете GitHub #8. ПОБОЧНАЯ НАХОДКА, не входившая в задачу: два теста в test_checklist_hardgate.py были красными на любой машине, где существует ~/.tausik. Причина — gotcha #385: обнаружение проекта идёт вверх по дереву и принимает каталог пользовательского тира конфига за корень проекта, поэтому chdir во временный каталог терял силу. В CI такого каталога нет, и тесты были зелёными. Закреплено явным TAUSIK_DIR; корневая причина остаётся за user-tier-config-recreates-the-directory-18-removed.
