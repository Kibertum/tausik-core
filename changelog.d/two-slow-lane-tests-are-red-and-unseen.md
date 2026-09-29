<!-- lang: en -->
### Fixed — two slow-lane tests were red, and nothing ran them

`pytest -q` deselects `-m slow`, and CI, which runs the full lane, does not run on a branch
that may not be pushed. Two tests therefore stayed red unseen. Both were broken by
intentional changes in the same release, not earlier, as `git bisect` shows:

- `test_mcp_integration` expected the MCP server to refuse a launch without `--project`.
  Since the server resolves the project per request (a4219bdf), that refusal is gone by
  design. The test now checks the new contract end to end: launched outside any project,
  the server still lists its tools and answers a call with the way out.
- `test_tausik_cli::test_full_lifecycle` closed a task without a verify run. Since the
  static gates also run on `verify` (2d192942), **QG-2 applies to every project, including
  one with no test gate**. Before that change, a project with no verify-trigger gate
  skipped Verify-First entirely. The test now closes the way a user does,
  `task done --ac-verified --relevant-files ... --verify`, and asserts that a fileless
  close without verify is refused. It no longer switches off each verify gate by name.

<!-- lang: ru -->
### Исправлено — две slow-ленты были красными, и их никто не гонял

`pytest -q` исключает `-m slow`, а CI, где гоняется полная лента, не запускается на
ветке, которую нельзя пушить. Поэтому два теста оставались красными незаметно. Оба
сломаны намеренными изменениями этого же релиза, а не раньше, что показывает `git bisect`:

- `test_mcp_integration` ждал, что MCP-сервер откажет в запуске без `--project`.
  С тех пор как сервер определяет проект на каждый запрос (a4219bdf), такого отказа
  больше нет, и это задумано. Теперь тест проверяет новый контракт сквозным прогоном:
  сервер, запущенный вне проекта, всё равно отдаёт список инструментов и отвечает
  на вызов подсказкой, что делать дальше.
- `test_tausik_cli::test_full_lifecycle` закрывал задачу без прогона verify. С тех пор
  как статические гейты запускаются и на `verify` (2d192942), **QG-2 действует в любом
  проекте, даже без тестового гейта**. До этого изменения проект без гейтов с триггером
  `verify` пропускал Verify-First целиком. Теперь тест закрывает задачу так же, как
  пользователь: `task done --ac-verified --relevant-files ... --verify`, и проверяет,
  что закрытие без файлов и без verify отклоняется. Выключать каждый verify-гейт
  поимённо тест больше не нужно.
