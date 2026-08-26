---
slug: subprocess-run-bez-yavnoy-encoding-prevraschaet-padenie-v
title: "subprocess.run без явной encoding превращает падение в тихое «не знаю»"
type: gotcha
tags:
  - encoding
  - silent-failure
  - subprocess
  - windows
task: closure-evidence-references-rot-and-nothing-notices
edges: []
---

Windows: subprocess.run(..., text=True) без encoding берёт кодовую страницу консоли (cp1252). Любой вызов, чей вывод содержит кириллицу — а `git log`, `git show`, `ruff`, `pytest` по этому репозиторию её содержат, — роняет UnicodeDecodeError в ЧИТАЮЩЕМ ПОТОКЕ subprocess. Исключение не долетает до вызывающего кода как ошибка: оно всплывает как PytestUnhandledThreadExceptionWarning, а обёртка, ловящая (OSError, SubprocessError), видит просто пустой или отсутствующий результат и рапортует «не смог определить».

Замер сессии #186 на audit_closure_evidence: пять цитат были помечены UNKNOWN_HISTORY вместо ROTTED. Отчёт выглядел честным — «git не ответил» — а на деле git ответил, и ответ был выброшен декодером.

ВСЕГДА писать явно: encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL. Идиома уже есть в gate_command_runner.py — копировать оттуда, а не изобретать.

Проверяется мутацией: снять encoding и прогнать тест, вызывающий команду с неанглийским выводом РЕАЛЬНОГО репозитория. На фикстуре из ASCII такой тест зелен всегда и не проверяет ничего.
