<!-- lang: en -->
### Added — the handoff says what colour the slow lane is

`pytest -q` deselects `-m slow`, and CI does not run on a branch that may not be pushed,
so a red slow test could live a whole session unseen. A whole-tree slow run
(`pytest -m slow` or `-m ''`) now leaves its verdict in `.tausik/slow_lane.json`. The
generated handoff reads it and carries `slow_lane`: `green`, `RED` with counts, or
`NOT RUN this session`. A project that records no lane gets no field. `/checkpoint` runs
the lane once, in the background, where the record exists. Under xdist the run summary
now also names the deselected count, which pytest's own summary line omits there.

<!-- lang: ru -->
### Добавлено — handoff называет цвет медленной ленты

`pytest -q` исключает `-m slow`, а CI не запускается на ветке, которую нельзя пушить,
поэтому красный slow-тест мог прожить всю смену незамеченным. Теперь прогон медленной
ленты по всему дереву (`pytest -m slow` или `-m ''`) оставляет итог в
`.tausik/slow_lane.json`. Сгенерированный handoff читает его и выводит поле `slow_lane`:
`green`, `RED` с числами или `NOT RUN this session`. Если проект ленту не записывает,
поля нет. Там, где запись есть, `/checkpoint` один раз прогоняет ленту в фоне. Под xdist
итог прогона теперь называет и число deselected, которое собственная итоговая строка
pytest в этом режиме опускает.
