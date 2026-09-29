<!-- lang: en -->
### Added — one changelog file per task instead of every task editing the same two lines

The continuous-changelog gate asks each closing task for an added line in `CHANGELOG.md`
AND `CHANGELOG.ru.md`, and every entry goes to the head of the same `[Unreleased]`
section. With parallel lanes that is a conflict on EVERY closed task in both languages —
not occasionally, but always, because everyone writes into the first lines of one section.
Of the three shared files a lane touches this is the only one that conflicts every time.

A task now writes `changelog.d/<slug>.md`, named after itself, which cannot collide by
construction. `tausik changelog assemble --apply` folds every fragment into both files in
slug order and removes them. Stdlib only, no new dependency.

**BOTH LANGUAGES IN ONE FILE.** The project ships a pair and half a pair is not an entry,
so the fragment carries `<!-- lang: en -->` and `<!-- lang: ru -->` and is refused without
either. Two files per task would let one language be forgotten in exactly the way the
parity test exists to catch.

**THE GATE DID NOT GET WEAKER.** It accepts a second proof, not a smaller one: a fragment
that is missing, empty, half-written or unparseable falls through to the git check that
was there before, and a task with neither route is refused exactly as it always was.
Assembly reads every fragment before writing anything, so a malformed one stops the fold
instead of leaving some folded and others deleted with nothing to show for them.

<!-- lang: ru -->
### Добавлено — один файл changelog на задачу вместо правки одних и тех же двух строк

Гейт непрерывного changelog требует от каждой закрываемой задачи добавленной строки в
`CHANGELOG.md` И `CHANGELOG.ru.md`, а все записи идут в шапку одного и того же раздела
`[Unreleased]`. При параллельных полосах это конфликт на КАЖДОЙ закрытой задаче в обоих
языках — не изредка, а всегда, потому что все пишут в первые строки одного раздела. Из
трёх общих файлов, которых касается полоса, этот единственный конфликтует постоянно.

Теперь задача пишет `changelog.d/<slug>.md`, названный по ней самой, — столкнуться такие
файлы не могут по построению. `tausik changelog assemble --apply` склеивает фрагменты в
оба файла в порядке слагов и удаляет их. Только stdlib, новой зависимости не появилось.

**ОБА ЯЗЫКА В ОДНОМ ФАЙЛЕ.** Проект поставляет пару, и половина пары — не запись, поэтому
фрагмент несёт `<!-- lang: en -->` и `<!-- lang: ru -->` и отказывается без любого из них.
Два файла на задачу позволили бы забыть один язык ровно так, как ловит тест паритета.

**ГЕЙТ НЕ ОСЛАБ.** Он принял второе доказательство, а не меньшее: отсутствующий, пустой,
недописанный или неразбираемый фрагмент проваливается в прежнюю проверку по git, а задача
без обоих путей отказывается как и раньше. Сборка читает все фрагменты до первой записи,
поэтому испорченный останавливает склейку, а не оставляет часть вклеенной и часть
удалённой впустую.
