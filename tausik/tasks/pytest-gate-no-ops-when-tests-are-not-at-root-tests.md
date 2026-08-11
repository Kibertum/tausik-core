---
slug: pytest-gate-no-ops-when-tests-are-not-at-root-tests
title: "Гейт pytest молча вырождается в no-op, когда тесты лежат не в <root>/tests"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: complex
role: backend
stack: null
tier: moderate
call_budget: 55
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/gate_test_resolver.py"
  - "scripts/gate_test_citation.py"
  - "scripts/*.py"
  - "tests/*.py"
scope_tools: []
completed_at: null
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
