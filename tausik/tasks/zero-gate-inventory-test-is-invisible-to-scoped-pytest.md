---
slug: zero-gate-inventory-test-is-invisible-to-scoped-pytest
title: "Новый тест-инвентарь обходит дерево исходников и невидим scoped-гейту"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: review-209-third-door-and-input-redirect-label
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_zero_gate_verdict.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-04T11:54:25Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

НАЙДЕНО ПОЛНОЙ ЛЕНТОЙ В КОНЦЕ СМЕНЫ #209, ХРАПОВИКОМ ВИДИМОСТИ. test_crosscutting_registry::test_new_tree_iterator_must_declare_or_optout красный: tests/test_zero_gate_verdict.py обходит дерево исходников (os.walk по scripts/ и harness/ в тесте инвентаря мест вызова lookup_recent_for_task), но не объявляет CROSSCUTTING_SCOPE и не отказывается от него явно.
ПОЧЕМУ ЭТО НЕ ФОРМАЛЬНОСТЬ. Scoped-pytest подбирает тесты ПО ИМЕНАМ файлов из relevant_files. Тест, чей предмет — ВСЁ дерево, ни на одно имя не мапится, поэтому при правке, например, scripts/hooks/*.py он не запускается. Именно он обязан краснеть на появлении четвёртого читателя примитива — то есть охрана, поставленная в предыдущей задаче, при scoped-прогоне молчала бы. Ровно тот класс, что чинился всю смену: контроль, который не выполняется, выглядит как контроль, который ничего не нашёл.
ЧТО ДЕЛАЕТСЯ: объявить CROSSCUTTING_SCOPE со списком охраняемых префиксов путей, чтобы scoped-гейт подтягивал этот тест при правках в них.

## Acceptance Criteria

AC-1: tests/test_zero_gate_verdict.py объявляет CROSSCUTTING_SCOPE с префиксами тех деревьев, которые он обходит, и храповик видимости зелёный.
AC-2 (негативный сценарий): прогон test_crosscutting_registry на текущем состоянии КРАСНЫЙ и называет этот файл — это и есть доказательство, что дефект был; после правки зелёный. Отказ от охраны пустым списком считается провалом: тест обходит дерево по-настоящему и обязан подтягиваться, а не выписываться из проверки.

## Plan

## Rollback

git revert <commit>: снимается объявление CROSSCUTTING_SCOPE, храповик снова краснеет. Кода продукта правка не касается.

## Journal

- 2026-09-04T11:53:43Z [implementation] — Root cause (missing-validation): новый тест инвентаря обходит scripts/ и harness/ целиком, поэтому его предмет — ВСЁ дерево, и scoped-pytest, подбирающий тесты по ИМЕНАМ файлов из relevant_files, не выбрал бы его ни при какой правке в этих деревьях. Я добавил обход по os.walk во втором круге починки (реагируя на находку ревью о плоском листинге) и не заметил, что расширение охвата теста ОТКЛЮЧАЕТ его в scoped-прогоне: охрана, обязанная краснеть на четвёртом читателе примитива, при scoped-verify молчала бы. Это ровно тот класс, который смена чинила весь день: контроль, который не выполнился, неотличим от контроля, который ничего не нашёл. Prevention: расширяя тест до обхода дерева, В ТОМ ЖЕ шаге объявляй CROSSCUTTING_SCOPE с префиксами обходимых деревьев; храповик test_new_tree_iterator_must_declare_or_optout ловит это, но ловит на ПОЛНОЙ ленте, а не на scoped-прогоне задачи — то есть после закрытия задачи, если полную ленту не гонять. Negative: негативная сторона предъявлена самим порядком событий — прогон храповика ДО правки красный и называет tests/test_zero_gate_verdict.py (текст падения в журнале смены), после правки зелёный. Отказ пустым списком CROSSCUTTING_SCOPE = [] был бы провалом AC-2: тест обходит дерево по-настоящему и обязан подтягиваться, а не выписываться из проверки. AC-1: ✓ tests/test_crosscutting_registry.py::TestCrosscuttingVisibility::test_new_tree_iterator_must_declare_or_optout AC-2: ✓ tests/test_crosscutting_registry.py::TestCrosscuttingVisibility::test_new_tree_iterator_must_declare_or_optout Domain: осмысленность вне тестов — при правке scripts/hooks/*.py в реальной задаче scoped-verify теперь подтянет этот тест, и появление четвёртого читателя примитива будет поймано в момент правки, а не на полной ленте в конце смены.
