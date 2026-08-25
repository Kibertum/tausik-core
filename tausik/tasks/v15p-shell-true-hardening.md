---
slug: v15p-shell-true-hardening
title: "[P1] Security: убрать shell=True из gate_command_runner"
status: done
epic: v15-polish
story: v15p-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/gate_command_runner.py — заменить shell=True ветку на shell-less исполнитель пайплайнов. tests/test_gate_command_runner*.py — добавить injection-тест."
scope_exclude: "stacks/*/stack.json (команды не трогаем), gate_runner.py, service_gates.py"
relevant_files:
  - "scripts/gate_command_runner.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T09:12:07Z"
---

## Goal

Техдолг #8 аудита: shell=True для команд с |/&& в custom stacks — вектор command injection. Заменить на явный pipeline-парсинг (shlex + subprocess chain) либо валидацию/allowlist шаблонов команд стека. AC: shell=True отсутствует или изолирован за строгой валидацией; тест с injection-payload в custom stack падает безопасно; существующие 25 gates проходят.

## Acceptance Criteria

1. shell=True отсутствует в gate_command_runner.py (или изолирован за строгой валидацией операторов). 2. Тест с injection-payload (`ruff; rm -rf ~`, `$(...)`, backtick) в custom-stack команде падает безопасно — деструктивная часть не исполняется. 3. Существующие gate-тесты проходят (pytest tests/test_gate*.py зелёный). 4. Реальные стек-команды (`terraform fmt -check && terraform validate`, `cmd 2>&1 | head -N`) работают как раньше.

## Plan

## Rollback

git revert коммита задачи; поведение gate-раннера откатывается на shell=True ветку. Стек-команды не менялись, миграций нет.

## Journal

- 2026-06-13T09:11:33Z [implementation] — shell=True убран: _run_shellless() токенизирует через shlex(punctuation_chars), исполняет только && и |, остальные операторы (;, $(), >>, backtick) -> _GateCommandError -> gate fail-safe. 13 новых тестов + 121 существующий зелёные. Bootstrap синхронизировал .claude/.
- 2026-06-13T09:11:56Z [implementation] — AC1 PASS: shell=True удалён из gate_command_runner.py; исполнение через _run_shellless (grep shell=True -> 0 совпадений). AC2 PASS: test_gate_shellless.py::TestRejectsInjection — ;-chain, $(), >> отклоняются с unsupported shell operator, sentinel-файл не создаётся. AC3 PASS: pytest tests/test_gate_shellless.py tests/test_gate_truncation_pipe.py tests/test_gates.py = 121 passed. AC4 PASS: TestSupportedOperatorsStillWork — && (terraform shape, short-circuit), | (pipe), 2>&1 merge работают.
- 2026-06-13T09:12:04Z [implementation] — AC verified: 1. shell=True удалён, исполнение через _run_shellless. 2. injection (;-chain, $(), >>) отклоняется, sentinel не создаётся. 3. pytest 121 passed. 4. && / | / 2>&1-merge работают (TestSupportedOperatorsStillWork).
