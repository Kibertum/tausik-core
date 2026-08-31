---
slug: windows-tausik-tausik-iz-subprocess-ne-zapuskaetsya-nuzhen
title: "Windows: .tausik/tausik из subprocess не запускается — нужен cmd /c ...tausik.cmd плюс PYTHONIOENCODING=utf-8"
type: gotcha
tags:
  - cli
  - encoding
  - subprocess
  - windows
task: this-repos-strictness-lives-in-a-gitignored-file
edges: []
---

Замерено в #197 при закрытии задачи с длинным --evidence (вложенные кавычки -> команда пишется файлом, конвенция уже есть).

Три отдельных грабли подряд в одном вызове:
1. `.tausik/tausik` — shell-скрипт без расширения. `subprocess.run([".tausik/tausik", ...])` падает `FileNotFoundError [WinError 2]`: CreateProcess такое не исполняет.
2. `.tausik\tausik.cmd` напрямую в списке — тоже `WinError 2`. CreateProcess не исполняет .cmd/.bat; нужен `["cmd", "/c", <абсолютный путь к .tausik\\tausik.cmd>, ...]`.
3. Команда отрабатывает, а `sys.stdout.write(r.stdout)` падает `UnicodeEncodeError: 'charmap' codec ... '⚠'` — вывод TAUSIK содержит ⚠, консоль cp1252. Задача при этом УЖЕ ЗАКРЫТА: исключение прилетело ПОСЛЕ успешного вызова, и по трейсбеку это неотличимо от провала. Повторный запуск ответил «already done» — это и был единственный способ узнать исход.

**Как применять:** запускай через `["cmd", "/c", ...]`, ставь `PYTHONIOENCODING=utf-8` внешнему python-у, а `subprocess.run` вызывай с `encoding="utf-8", errors="replace"`. И ПЕРЕД повторной попыткой проверяй состояние (`task show`), а не трейсбек: падение печати выглядит как падение команды.
