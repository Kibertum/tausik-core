<!-- lang: en -->
### Fixed — `test_dedupe` no longer measures the framework inside your project

Run from the framework's own tree, the duplicate-test gate counted TAUSIK's tests
instead of the project's, so a project could be refused a close for debt that was not
its own. It now measures the project whose `.tausik/` it runs for; a project without a
baseline gets "NOT ADOPTED", as before.

<!-- lang: ru -->
### Исправлено — `test_dedupe` больше не мерит фреймворк внутри вашего проекта

Запущенный из дерева самого фреймворка, гейт дублирующихся тестов считал тесты TAUSIK
вместо тестов проекта, и проекту могли отказать в закрытии за чужой долг. Теперь он
мерит проект, для чьего `.tausik/` запущен; проект без базы получает «NOT ADOPTED», как
и раньше.
