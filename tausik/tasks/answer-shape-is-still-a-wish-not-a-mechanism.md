---
slug: answer-shape-is-still-a-wish-not-a-mechanism
title: "Форма ответа осталась текстом-пожеланием: медиана выросла 396 → 522 при бюджете 200"
status: done
epic: release-110-deferred-from-19
story: release110-terse-answers
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: terse-answers-enforced-by-mechanism
scope: null
scope_exclude: null
relevant_files:
  - CLAUDE.md
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_response_contract_shape.py"
  - "tests/test_caveman_output_mode.py"
  - "tests/test_instruction_tone.py"
scope_paths:
  - CLAUDE.md
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_caveman_output_mode.py"
  - "tests/test_bootstrap_generate.py"
  - "tests/test_response_contract_shape.py"
  - "tests/test_rules_generator_warning_parity.py"
  - "tests/test_instruction_tone.py"
  - "docs/ru/agent-contract.md"
  - "docs/en/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T11:45:15Z"
resolution: null
resolution_reason: null
tracker_refs: []
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

Форма ответа (done → verified by → left → your call) стоит в ПРАВИЛАХ, которые читаются каждый ход, а не в опциональном скилле и не в подсказке ПОСЛЕ отправки. Замер: медиана финального ответа 522,5 слова при бюджете 200, p90 923 — против 396/915 до 1.10, то есть хуже, хотя история J закрыта как сделанная.

## Acceptance Criteria

1. Четыре части формы стоят в CLAUDE.md этого проекта — файле, который читается каждый ход, — а не только в скилле; бюджет статической части 4096 байт не превышен. 2. Порождаемые инструкции пользователя несут ту же форму НЕЗАВИСИМО от output_mode: сегодня шаблон упоминает /i-have-adhd как скилл в списке, то есть пользователь получает ссылку, а не правило. 3. НЕГАТИВНЫЙ: граница TAUSIK сохранена дословно — форма не сокращает журналы, доказательства AC, квитанции, вывод гейтов, находки безопасности и докстринги. 4. НЕГАТИВНЫЙ: блокирующий Stop-хук НЕ используется — прецедент keyword-detector-self-trigger-loop: блокировка Stop съедает вывод хода, и ответ, ради краткости которого всё делается, не доходит вовсе. 5. Полная лента зелёная.

## Plan

## Rollback

git revert; правка текстовая плюс строка в CLAUDE.md. Механизм аддитивен: без него поведение то же, что сегодня.

## Journal

- 2026-09-29T11:43:01Z [implementation] — AC-1: ✓ строка формы стоит в CLAUDE.md проекта; запас 209 байт из 4096, храповик MIN_HEADROOM_BYTES=180 зелёный. Заплачено: выброшена доктринальная строка SENAR из Принципов — она не меняет ни одного действия, это правило допуска, записанное в самом файле. AC-2: ✓ ANSWER_SHAPE поставляется в обоих тирах порождаемых инструкций независимо от output_mode — tests/test_response_contract_shape.py::test_the_contract_ships_with_the_mode_off и tests/test_caveman_output_mode.py::TestCarveOuts::test_the_shape_ships_with_the_mode_off. За caveman осталось только сжатие прозы, потолок 888 → 358 по замеру.
- 2026-09-29T11:43:02Z [implementation] — AC-3 НЕГАТИВНЫЙ: ✓ ::test_the_record_is_protected_whether_or_not_the_mode_is_on — проверяет ПОРОЖДЁННОЕ ТЕЛО при обоих значениях режима, а не константу; раньше гарантия была условной при выключенном режиме. Контракт поставляется целиком: первый заход сжал его и молча выбросил три элемента, ::test_response_contract_shape поймал все три. AC-4 НЕГАТИВНЫЙ: ✓ блокирующий Stop НЕ используется — dead-end #797, прецедент keyword-detector-self-trigger-loop: харнесс отдаёт блокировку Stop как ошибку хука и ход умирает без вывода. AC-5: ✓ полная лента 12233 прошли, 35 пропущены.
- 2026-09-29T11:44:18Z [implementation] — Root cause (config-error): контракт ответа существовал дважды и оба раза за переключателем — output_mode со значением off по умолчанию и скилл, который надо вызвать. Замер показал результат: медиана 522 слова при бюджете 200, хуже 396 до появления контракта. Prevention: правило, адресованное агенту, ставится в файл правил, читаемый каждый ход, а не в опциональный режим; проверка читает ПОРОЖДЁННОЕ ТЕЛО, а не константу, — тогда она не может пройти, пока правила пользователя без правила. Обратная сторона записана дохлым концом: enforcement через блокирующий Stop съедает вывод хода.
