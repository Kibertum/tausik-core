---
slug: bash-c-wrapper-bypasses-qg0-write-gate
title: "`bash -c 'echo x > file'` обходит QG-0 и scope-ACL целиком — обёртка интерпретатора не разбирается"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/hooks/bash_write_parse.py, tests/test_bash_write_gate_hook.py, tests/test_memory_sinks.py, docs/ru/agent-contract.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/hooks/bash_write_gate.py и memory_pretool_block.py — потребители, их логика не меняется, они просто получат более полный ответ. scripts/hooks/bash_firewall.py — отдельный гейт опасных команд, другой вопрос. Остальные вектора остаточной границы (переменные в путях, base64|sh, sudo tee, curl -O) — НЕ в этой задаче, граница по ним остаётся документированной."
relevant_files:
  - "scripts/hooks/bash_write_parse.py"
  - "tests/test_bash_write_gate_hook.py"
  - "tests/test_memory_sinks.py"
  - "docs/ru/agent-contract.md"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-24T00:12:57Z"
---

## Goal

Найдено dogfooding'ом в сессии #132. `bash_write_parse.write_targets("bash -c 'printf x > .clinerules'")` возвращает `[]`; то же для `sh -c "..."`. Перенаправление живёт внутри ОДНОГО закавыченного аргумента, поэтому ни один детектор его не видит. Следствие: правило «нет кода без задачи» (SENAR Rule 1, QG-0) и scope-ACL (Rule 2) обходятся однострочником `bash -c 'echo ... > src/foo.py'` — ровно тот класс, который l26-hook-contract-review закрывал для heredoc'а (Decision #162). Документированная остаточная граница утверждала, что цена обхода поднята до «нужно намеренно обфусцировать»; `bash -c` — не обфускация, это повседневная форма. Формулировка уже исправлена в docs/ru/agent-contract.md, дыра названа; здесь её надо закрыть. Направление: при `base` in (bash, sh, zsh, dash) и наличии `-c` рекурсивно разобрать payload через write_targets и добавить найденные цели. Осторожно: рекурсия должна иметь предел глубины и не должна ломать существующее поведение (`_mentions_interpreter` + _OPEN_RE для python -c уже есть). Затрагивает bash_write_gate (QG-0), memory_pretool_block и любой будущий потребитель — то есть требует прогонов на false-positive по всей suite.

## Acceptance Criteria

1. Воспроизведение ДО фикса: тест показывает, что `bash -c 'echo x > scripts/foo.py'` и `sh -c "..."` дают ноль целей записи, то есть QG-0 и scope-ACL обходятся однострочником.
2. `write_targets` рекурсивно разбирает payload оболочки при `base` из {bash, sh, zsh, dash, ksh} и наличии флага `-c` (включая слитные формы вроде `-lc`, `-ec`); найденные цели добавляются к остальным.
3. Рекурсия ограничена по глубине явной константой — `bash -c "bash -c '...'"` не должен уходить в бесконечность; предел объявлен и покрыт тестом.
4. NEGATIVE — никаких новых false-positive: `bash --version`, `bash script.sh` (без -c), `bash -c 'pytest -q'`, `echo 'bash -c \"x > y\"'` (упоминание в кавычках) не дают целей. Полный прогон suite зелёный без правок в прочих тестах — если какой-то тест падает, это НАСТОЯЩАЯ новая находка, разобрать её, а не подогнать тест.
5. Уверенность парсера (`write_targets_with_confidence`) корректна и для рекурсивной ветки: непарсящийся payload не превращает уверенный ответ в `parsed`.
6. Совместно с memory_route: рекурсивно найденная цель в чужом memory-стоке блокируется хуком (тест на `bash -c 'echo x > .clinerules'`).
7. docs/ru/agent-contract.md: раздел про обёртку `bash -c` переписан с «дыра, заведена задачей» на актуальное состояние; остаточная граница переформулирована честно под новое поведение.
8. Все гейты зелёные; полный прогон pytest зелёный.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

git revert коммита. Изменение локализовано в bash_write_parse (одна ветка разбора + константа глубины); откат возвращает прежнее — более слабое, но работоспособное — поведение обоих потребителей. Хуки независимо отключаются TAUSIK_SKIP_HOOKS=1 (пишет bypass-событие).

## Journal

- 2026-07-24T00:03:45Z [implementation] — Реализовано: _shell_payloads (7 оболочек, флаг -c включая слитные -lc/-ec, длинная опция НЕ считается кластером коротких) + _parse с явной глубиной и именованным _MAX_WRAPPER_DEPTH=3. write_targets_with_confidence переведён на _parse; непарсящийся payload роняет ВЕСЬ ответ до regex_fallback — вернуть более уверенное из двух чтений неправильно для потребителя, который на неопределённости закрывается. Внутренности парсера (_writers_in, _split_subcommands, _redir_targets_regex) снаружи никем не импортируются — проверено grep'ом до правки, поэтому изменение формы _parse безопасно. ПОДТВЕРЖДЕНИЕ ЦЕННОСТИ ТЕСТА-ПИНА: тест test_interpreter_wrapper_hides_the_target, написанный ПРЕДЫДУЩЕЙ задачей специально чтобы закрепить дыру, упал ровно тогда, когда я научил парсер рекурсии, — то есть изменение заявило о себе, а не прошло молча. Перевёрнут в test_interpreter_wrapper_no_longer_hides_the_target. Это ровно та польза, ради которой пин и ставился. Негативы закреплены отдельно (AC4): bash --version, bash script.sh, bash -c 'pytest -q', echo с упоминанием в кавычках, bash --color=auto -c. Более строгий парсер оправдан только если молчит на обычном.
- 2026-07-24T00:12:55Z [implementation] — AC1 ✓ Воспроизведение зафиксировано ТЕСТОМ, написанным предыдущей задачей (test_interpreter_wrapper_hides_the_target), который утверждал ноль целей для bash -c / sh -c. Он упал ровно при этом изменении — то есть дыра существовала и была закреплена документально. AC2 ✓ _shell_payloads: bash, sh, zsh, dash, ksh, ash, busybox; флаг -c распознаётся и в слитных формах (-lc, -ec); payload разбирается рекурсивно через _parse, цели добавляются к остальным. Параметризованный тест на 7 форм, включая вложенную bash -c "bash -c '...'", tee и sed -i внутри payload'а. AC3 ✓ Предел вложенности — именованная константа _MAX_WRAPPER_DEPTH=3, не неявная глубина рекурсии. test_recursion_is_bounded строит цепочку глубже предела и требует, чтобы вызов ВЕРНУЛСЯ. AC4 NEGATIVE ✓ Ни одного нового false-positive: bash --version, bash script.sh (без -c аргумент — файл для запуска), bash -c 'pytest -q', echo с упоминанием в кавычках, bash --color=auto -c (длинная опция не кластер коротких), python -m pytest. ГЛАВНОЕ: полный прогон 5574 passed / 0 failed — более строгий парсер не потребовал правки НИ ОДНОГО существующего теста, кроме намеренного пина из AC1. AC5 ✓ test_unparseable_payload_degrades_the_whole_confidence: внешняя команда токенизируется, payload нет → ответ regex_fallback, а не parsed. Вернуть более уверенное из двух чтений неправильно для потребителя, который на неопределённости закрывается. AC6 ✓ test_blocks_write_hidden_behind_a_shell_wrapper: хук memory_pretool_block возвращает exit 2 на bash -c 'echo x > .clinerules'. AC7 ✓ docs/ru/agent-contract.md: раздел переписан с «дыра, заведена задачей» на «ЗАКРЫТА», перечислены оболочки, флаги, предел вложенности и что НЕ считается целью. AC8 ✓ Все task-done гейты зелёные; ruff All checks passed; verify #1234 подписан. CHANGELOG ✓ [Unreleased] EN + RU-зеркало. Domain: осмысленно вне тестов — bash -c это форма, которой пишут ежедневно, и до фикса ею обходилось headline-правило фреймворка «нет кода без задачи». Проверено на живых формах команд, а не только на синтетике. Root cause (edge-case): детекторы целей записи работали по ТОКЕНАМ команды, а payload оболочки — это один непрозрачный токен, внутри которого живёт своя команда. Ни один детектор не был неправ; неправым было допущение, что один уровень токенизации исчерпывает вход. Prevention: для любого парсера входа, где элемент может САМ БЫТЬ входом того же языка (shell -c, eval, xargs, ssh host cmd, docker run), проверять рекурсию явным тестом до объявления границы — и не описывать остаточную границу словами сильнее, чем подтверждено прогоном.
