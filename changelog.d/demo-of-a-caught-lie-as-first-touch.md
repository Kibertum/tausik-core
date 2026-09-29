<!-- lang: en -->
### Added — `tausik demo`: watch a false "tests pass" get caught

`tausik demo` runs a scripted scenario in a throwaway sandbox, in about ten seconds, with
no network and no LLM key: the agent claims the tests are green without running them,
the close is refused, the real check runs red, and only an actual fix closes the task
with a signed receipt. Every line it prints is the real CLI's output. The README now
opens with it, above the install steps.

### Fixed — three gates located "the project" from their own file

Found by running the demo from the framework's own tree. `ruff_format` refused a
project on another drive ("path is on mount 'C:', start on mount 'D:'"), `test_dedupe`
measured the framework's tests inside another project's close, and
`cross_model_parity` crashed from the deployed copy because it looked for the bootstrap
sources under `.claude/`. All three now find the project from its `.tausik/` directory;
parity reports "not applicable" where there is no bootstrap source.

<!-- lang: ru -->
### Добавлено — `tausik demo`: посмотреть, как ловится ложное «тесты прошли»

`tausik demo` разыгрывает сценарий в одноразовой песочнице примерно за десять секунд,
без сети и без ключа LLM: агент заявляет, что тесты зелёные, не запуская их, закрытие
отклоняется, настоящая проверка красная, и только реальная правка закрывает задачу с
подписанной квитанцией. Каждая напечатанная строка — настоящий вывод CLI. README теперь
начинается с неё, выше шагов установки.

### Исправлено — три гейта искали «проект» от собственного файла

Найдено запуском демо из дерева самого фреймворка. `ruff_format` отказывал проекту на
другом диске («path is on mount 'C:', start on mount 'D:'»), `test_dedupe` мерил тесты
фреймворка внутри закрытия чужого проекта, а `cross_model_parity` падал из развёрнутой
копии, потому что искал исходники bootstrap под `.claude/`. Все три теперь находят
проект по его каталогу `.tausik/`; сверка паритета там, где исходников bootstrap нет,
пишет «неприменимо».
