---
slug: test-proliferation-has-a-report-but-no-gate
title: "Размножение тестов ловится отчётом, а не гейтом — и tests/ освобождён от единственного размерного правила"
status: done
epic: release-19-renar-conformance
story: test-evidence-not-test-volume
complexity: simple
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: null
scope_exclude: "освобождение tests/ от гейта размера НЕ трогаем — задача прямо говорит пересмотреть его ОТДЕЛЬНЫМ решением; сам детектор audit_pytest_dedupe.py не переписываем, только читаем его результат; удаление или слияние существующих дублей в этой задаче не делается"
relevant_files:
  - "scripts/gate_test_dedupe.py"
  - "scripts/gate_registry.py"
  - "scripts/gate_spec.py"
  - "tausik/gates.json"
  - "tests/test_gate_test_dedupe.py"
  - "tests/test_gates_catch_their_violation.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/gate_test_dedupe.py"
  - "scripts/gate_registry.py"
  - "scripts/gate_spec.py"
  - "tausik/gates.json"
  - "tests/test_gate_test_dedupe.py"
  - "tests/test_gates_catch_their_violation.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-06T14:53:18Z"
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

ЗАМЕР, сессия #178: 403 файла тестов, 5722 функции, 92429 строк. Детектор дублей УЖЕ ЕСТЬ — scripts/audit_pytest_dedupe.py, у него есть флаг --check, и он задокументирован как «Static audit reports (review-only)». То есть проверка реализована и не блокирует НИЧЕГО — тот же узор, что у memory lint. Вторая половина: tests/ входит в _FILESIZE_EXEMPT_DIRS (gate_filesize.py), поэтому тесты суть единственное место в дереве вообще без размерной дисциплины. Задача: сделать детектор гейтом с ХРАПОВИКОМ — не хуже, чем сейчас, а известные 683 структурно одинаковых теста в 294 группах фиксируются как долг с числом, а не блокируют работу разом. Освобождение tests/ от гейта размера пересмотреть отдельным решением: оно могло быть верным, когда тестов было мало. НЕГАТИВНОЕ ограничение: гейт не имеет права поощрять удаление тестов ради зелёного счётчика — предмет проверки есть РАЗЛИЧИМОСТЬ, а не количество, и это ловится вместе с p9-a-test-never-observed-red-is-not-evidence.

## Acceptance Criteria

AC-1 (детектор становится гейтом): структурные дубли тестов проверяются гейтом на триггерах task-done и commit, а не только отчётом по запросу. Предмет замеряется существующим scripts/audit_pytest_dedupe.py, а не переписывается заново.
AC-2 (храповик, а не запрет разом): база фиксируется числом в закоммиченном tausik/gates.json рядом с остальными базами; сегодняшнее состояние (322 группы, 753 теста — ЗАМЕР, старая цифра #178 говорила 294/683, то есть долг вырос) не блокирует работу. Краснеет РОСТ.
AC-3 (храповик обязан сжиматься): база, оказавшаяся ВЫШЕ замера, — сама по себе провал: тест требует опустить её на достигнутое, иначе линия перестаёт быть храповиком и становится списком.
AC-4 NEGATIVE (гейт ловит именно рост): добавление структурно одинакового теста даёт красное с указанием, на сколько выросло и где; мутация, снимающая сравнение с базой, краснеет.
AC-5 NEGATIVE (гейт не поощряет удаление тестов ради счётчика): предмет — РАЗЛИЧИМОСТЬ, а не количество. Гейт не считает общее число тестов и не краснеет от их роста; удаление одного из пары неотличимых есть ЖЕЛАЕМОЕ действие, и это сказано в тексте гейта, а не подразумевается.
AC-6: мутации объявлены и убиты по ветви либо объявлены эквивалентными; полный прогон, mypy, ruff, bootstrap --check --ide all; команда описана в docs/{ru,en}/cli.md; CHANGELOG в обоих файлах; карта перевыпущена.

## Plan

## Rollback

git revert <commit>: гейт добавляется, ничего существующего не переписывает. Откат снимает регистрацию и узел test_dedupe из tausik/gates.json; детектор scripts/audit_pytest_dedupe.py остаётся как был — отчётом.

## Journal

- 2026-09-06T14:46:18Z [implementation] — AC verified: AC-1 (детектор стал гейтом): ✓ scripts/gate_test_dedupe.py зарегистрирован как test_dedupe (block, task-done + commit), предмет замеряется существующим audit_pytest_dedupe.collect_duplicates — детектор не переписан, а использован; стоимость полного скана 0.78 с на 403 файлах. ✓ tests/test_gate_test_dedupe.py::test_the_gate_is_registered_on_the_blocking_triggers AC-2 (храповик, а не запрет разом): ✓ база 322 группы / 753 теста записана в закоммиченный tausik/gates.json рядом с filesize и class_surface; гейт зелёный на репозитории, в котором появился. ЗАМЕР ПОДТВЕРДИЛ РОСТ ДОЛГА: #178 давал 294/683, сегодня 322/753 — детектор с флагом --check существовал и не запускался. ✓ tests/test_gate_test_dedupe.py::test_the_gate_is_green_on_the_repo_it_landed_on AC-3 (храповик обязан сжиматься): ✓ база ниже замера — провал теста с требованием опустить её. ✓ tests/test_gate_test_dedupe.py::test_the_baseline_only_ratchets_down AC-4 NEGATIVE (ловит именно рост): ✓ рост даёт красное, называет насколько и печатает крупнейшие группы файлом и строкой. Мутации S1 (сравнение с базой снято) и S3 (адреса убраны) убиты по ветви. ✓ tests/test_gate_test_dedupe.py::test_growth_is_red_and_says_where AC-5 NEGATIVE (удаление тестов не удовлетворяет гейт): ✓ гейт не измеряет общее число тестов; замер НИЖЕ базы — проход с требованием опустить базу, а не награда. Сказано в тексте гейта и в docs. Мутация S4 (улучшение не просит двигать базу) убита. ✓ tests/test_gate_test_dedupe.py::test_deleting_tests_can_never_satisfy_the_gate Плюс отказ вместо ложной зелени: нечитаемая база даёт красное, а не «дублей не записано». Мутация S2 убита. ✓ tests/test_gate_test_dedupe.py::test_an_unreadable_baseline_refuses_instead_of_passing AC-6: ✓ мутаций 4 по предмету, все KILLED по ветви (S5 отвергнута как мутация ТЕСТА, а не предмета, — записал прямо); мутатор удалён сразу. Полный прогон 9117 passed / 27 skipped, mypy Success 356 файлов, ruff чист, bootstrap --check без дрейфа. Команда отчёта описана в docs/ru/cli.md и docs/en/cli.md; CHANGELOG в обоих файлах. Domain: гейт отвечает на вопрос «стало ли в репозитории больше тестов, которые нельзя отличить друг от друга», и отвечает числом с адресами. Освобождение tests/ от гейта размера НЕ трогал — задача прямо оставляет его отдельному решению.
- 2026-09-06T14:53:09Z [implementation] — ГЕЙТ РАЗМЕРА ОТБИЛ ЗАКРЫТИЕ, И ЭТО ПОЧИНЕНО РАЗДЕЛЕНИЕМ, А НЕ ПОДРЕЗКОЙ КОММЕНТАРИЕВ. Добавленный GateSpec довёл scripts/gate_registry.py до 520 строк при лимите 500 (файл стоял на 499 — впритык). Подрезать объяснения ради лимита значило бы ровно ту деформацию, на которую жалуется решение #190 («модули резались, чтобы пройти»). Вместо этого вынес ЗАПИСЬ — GateSpec и константы фаз — в scripts/gate_spec.py: там ДЕКЛАРАЦИЯ (из чего состоит запись о гейте), в реестре ДАННЫЕ (какие гейты есть). Шов не произвольный: эти две вещи меняются по разным поводам — данные при каждом новом гейте, форма почти никогда. Обратная совместимость через реэкспорт: все существующие `from gate_registry import GateSpec, PHASE_SCOPED` работают, тесты реестра прошли без правок. Дублирующее объяснение про две фазы удалено из реестра — теперь оно живёт в одном месте. Итог: 490 и 55 строк, полный прогон 9117 passed, mypy Success 357 файлов, ruff чист.
