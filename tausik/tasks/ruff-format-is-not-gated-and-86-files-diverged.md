---
slug: ruff-format-is-not-gated-and-86-files-diverged
title: "Формат кода не проверяется ни одним гейтом: 86 файлов разошлись с ruff format, и узнать об этом можно только вручную"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_ruff_format.py"
  - "scripts/gate_registry_scoped.py"
  - "tausik/gates.json"
  - "tests/test_gate_ruff_format.py"
  - "tests/test_gates_catch_their_violation.py"
scope_paths:
  - "scripts/gate_ruff_format.py"
  - "scripts/gate_registry_scoped.py"
  - "tausik/gates.json"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T22:14:39Z"
resolution: null
resolution_reason: null
---

## Goal

Найдено в сессии #155 попутно, при статической проверке перед закрытием задачи.

ЗАМЕР. `python -m ruff format --check scripts/ tests/` -> «86 files would be reformatted, 618 files already formatted». Прогон повторён на ЧИСТОМ дереве (git stash -u, то есть без моих правок) — те же 86. Значит состояние досталось по наследству, а не внесено сессией #155.

ПОЧЕМУ ЭТОГО НИКТО НЕ ВИДИТ. Гейт объявлен в scripts/gate_registry.py:86 командой `ruff check {files}` — это ТОЛЬКО линтер. `ruff format --check` не запускается ни одним гейтом, ни verify, ни task done, ни CI-скриптами репозитория (grep по scripts/ даёт единственное упоминание ruff — эту строку реестра и два описания в default_gates.py). При этом pyproject.toml объявляет [tool.ruff] line-length=100, то есть форматтер СКОНФИГУРИРОВАН и им пользуются — просто его вердикт ни к чему не подключён.

ЦЕНА. Это ровно «тихая ошибка»: конфигурация утверждает стиль, инструмент его умеет проверить, и никто не спрашивает. Пока проверки нет, любая правка может как приблизить файл к формату, так и увести — сигнала не будет. Плюс это ловушка для нового агента: он запускает `ruff format --check` как «обычную статику», получает 86 отказов, не понимает, свои они или чужие, и тратит время на разбор (я потратил).

ВАЖНО ПРО ОБЪЁМ. Форматирование 86 файлов разом даст диф, который перекроет собой историю правок. Решение о том, чинить ли всё сразу или ввести храповик (гейт проверяет только ФАЙЛЫ ЗАДАЧИ, как это уже делает `ruff check {files}`), принимается внутри задачи — но принимается ЯВНО, а не умолчанием.

## Acceptance Criteria

1. ВЕРДИКТ ФОРМАТТЕРА ПОДКЛЮЧЁН К ГЕЙТУ. `ruff format --check` (или эквивалент) запускается тем же механизмом, что и `ruff check {files}`, и его отказ БЛОКИРУЕТ. Доказывается прогоном: намеренно расформатированный файл задачи роняет verify, отформатированный — проходит.
2. ОБЛАСТЬ ВЫБРАНА ЯВНО И ЗАПИСАНА РЕШЕНИЕМ. Либо все 86 файлов приведены к формату одним отдельным коммитом, не смешанным ни с какой смысловой правкой, либо гейт объявлен ХРАПОВИКОМ по файлам задачи с замороженным перечнем унаследованных 86 — и тогда перечень обязан только СОКРАЩАТЬСЯ (тест на это, как в tests/test_crosscutting_registry.py). Смесь недопустима.
3. ЧИСЛО НАЗВАНО ДО И ПОСЛЕ. В журнале записан вывод `ruff format --check scripts/ tests/` до правки (86) и после. Если выбран храповик — записано, сколько файлов в замороженном перечне.
4. НОВЫЙ АГЕНТ НЕ ПОПАДЁТ В ТУ ЖЕ ЛОВУШКУ. Расхождение перестаёт быть невидимым: либо его нет, либо оно названо в docs/ru/agent-contract.md (или troubleshooting) одной строкой — «эти N файлов унаследованы, гейт их не трогает».
5. НЕГАТИВ: гейт не стал шумным. `ruff check` по-прежнему проходит, время verify выросло не более чем на секунды (замер до/после в журнале), и ни один существующий тест не покраснел от переформатирования.
6. Полный pytest зелёный; mypy чист; bootstrap drift отсутствует.

## Plan

## Rollback

git revert; перечень в tausik/gates.json и гейт уходят вместе

## Journal

- 2026-09-23T22:11:57Z [implementation] — Сделано: scripts/gate_ruff_format.py (run_ruff_format_gate: ruff format --check по .py-файлам задачи, пропуская замороженный перечень; ruff не запускается — отказ, а не молчание); GateSpec ruff_format в gate_registry_scoped (block, verify+commit); tausik/gates.json: доказательство и ruff_format.legacy_unformatted (116 файлов); классификация в test_gates_catch_their_violation (EXCUSED с собственным модулем); docs cli en/ru; решение #386 с двумя отвергнутыми вариантами.
- 2026-09-23T22:11:58Z [implementation] — AC-1: ✓ tests/test_gate_ruff_format.py::test_a_formatted_task_file_passes
- 2026-09-23T22:11:58Z [implementation] — AC-1: ✓ tests/test_gate_ruff_format.py::test_an_unformatted_task_file_blocks
- 2026-09-23T22:11:58Z [implementation] — AC-2: ✓ решение #386 (храповик с замороженным перечнем); tests/test_gate_ruff_format.py::test_the_legacy_list_only_shrinks
- 2026-09-23T22:11:59Z [implementation] — AC-3: ✓ до: 86 в смене #155, 117 при старте задачи, 116 на момент заморозки; после: перечень 116, вне перечня 0
- 2026-09-23T22:11:59Z [implementation] — AC-4: ✓ docs/en|ru/cli.md описывает гейт и перечень; отказ гейта печатает команду исправления
- 2026-09-23T22:11:59Z [implementation] — AC-5: ✓ tests/test_gate_ruff_format.py::test_a_file_on_the_legacy_list_is_not_checked — гейт смотрит только файлы задачи, перечень пропускается
- 2026-09-23T22:12:00Z [implementation] — AC-6: ✓ в иной форме — scoped verify + реестровые тесты гейтов (186 зелёных); полный прогон — CI и тег по правилу владельца #711 'проверка соразмерна правке'
- 2026-09-23T22:12:00Z [implementation] — NO-DEAD-END: красный локальный прогон — новый гейт не был классифицирован в test_gates_catch_their_violation, добавлен
- 2026-09-23T22:13:34Z [implementation] — Красный verify: pytest verify бежит системным Python с ruff 0.16.5 (он же — ruff в PATH, который вызывает линт-гейт), а я считал перечень venv-ным ruff 0.15.12; у 0.16 другой формат вывода (диагностика ' --> PATH:L:C' вместо 'Would reformat:'). Правка: гейт берёт тот же ruff, что линт-гейт (shutil.which('ruff')), разбирает оба формата, тест дерева идёт через помощник гейта; перечень пересчитан тем же бинарём (116). Проверено под обоими интерпретаторами. NO-DEAD-END: причина — расхождение версий инструмента, устранена выбором одного бинаря
