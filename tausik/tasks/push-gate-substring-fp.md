---
slug: push-gate-substring-fp
title: "Хук git_push_gate ложно блокирует Bash-команды с подстрокой push в тексте"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/hooks/git_push_gate.py"
  - "tests/test_hooks.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-17T22:29:31Z"
---

## Goal

git_push_gate.py матчит подстроку в СЫРОЙ командной строке, из-за чего блокирует любую Bash-команду, ГДЕ в тексте (не в вызове) встречается 'git'+'push' — напр. tausik task log / memory add с описанием процедуры зеркалирования словили BLOCKED, хотя это не пуш. Нужно: парсить команду как аргументы и срабатывать только когда push — реальная git-подкоманда (argv[0]=git и есть подкоманда push), а не при вхождении в строковый литерал/аргумент другой программы. Проверено на сессии 2026-07-17.

## Acceptance Criteria

1. git_push_gate распознаёт команду по shlex-токенам (кавычки-строка = один токен), а не по подстроке в сырой строке. 2. FALSE-POSITIVE устранён: команда с биграммой 'git'+'push' внутри кавычек-аргумента (напр. tausik task log/memory add) НЕ блокируется (returncode 0). 3. TRUE-POSITIVE сохранён: реальная git-публикация без тикета блокируется (returncode 2) — путь-префикс (/usr/bin/git), -c флаги, цепочка после &&/;. 4. НЕГАТИВ: git commit -m с текстом-словом push НЕ блокируется (не в позиции подкоманды). 5. НЕКОРРЕКТНАЯ команда (несбалансированные кавычки, shlex падает) → консервативный fallback на старый regex (блокировать). 6. Юнит-тесты в test_hooks.py зелёные на 3.11 и 3.13; ruff чист; bootstrap-hooks-parity не сломан.

## Plan

## Rollback

git revert; хук возвращается к прежнему подстрочному матчеру

## Journal

- 2026-07-17T21:56:26Z [implementation] — Живая проверка фикса: эта запись содержит git push внутри аргумента и БОЛЬШЕ не блокируется хуком (токенное распознавание). Раньше такая же строка ловила BLOCKED.
- 2026-07-17T21:59:43Z [implementation] — Фикс: _command_invokes_git_push токенизирует через shlex, ищет git..push в позиции команды; кавычки-строка = один токен -> мнимая биграмма не матчится. Обобщены глобальные value-флаги (-c/-C/--git-dir). Fallback на regex при shlex ValueError. 10/10 unit-кейсов функции + 16/16 TestGitPushGate на 3.11 и 3.13 + 91 passed (hooks+doc+parity), ruff чист. Живая проверка: task log с биграммой прошёл (EXIT 0). +3 теста -> test_count 4744->4747, реген constants.json + бейджи README.md/README.ru.md. Коммит ce3a3d3 -> GitLab a5e01df..ce3a3d3, пайплайн 3819 идёт.
- 2026-07-17T22:29:31Z [implementation] — AC-1: ✓ _command_invokes_git_push токенизирует через shlex (кавычки-строка = один токен). AC-2: ✓ FP устранён — test_quoted_push_mention_not_treated_as_push returncode 0, живая проверка task log с биграммой прошла. AC-3: ✓ TP сохранён — 16/16 TestGitPushGate (реальная публикация, /usr/bin/git, цепочка &&, -c флаг блокируются). AC-4: ✓ негатив — test_commit_with_push_word_in_message_allowed returncode 0. AC-5: ✓ fallback на regex при shlex ValueError (несбалансированные кавычки). AC-6: ✓ GitHub-матрица run 29616818841 success все 11 ячеек + test-full + lint; GitLab 3819 success; ruff чист; bootstrap-parity 3/3. Domain: discipline-rail теперь блокирует только реальную публикацию, не мешая журналированию с упоминанием команды в тексте — семантика для настоящих пушей полностью сохранена (16/16). Checklist: scope (git_push_gate.py + test_hooks.py), тесты покрывают FP+TP+негатив+fallback, security surface сохранён, rollback = git revert.
