---
slug: absolyutnyy-put-mashiny-v-zhurnale-zadachi-ronyaet-geyt
title: "Абсолютный путь машины в журнале задачи роняет гейт публикации, а вычеркнуть его может только tausik redact — проекция Journal читает task_logs, не tasks.notes"
type: gotcha
tags:
  - gate
  - journal
  - publication
  - redact
  - state-export
task: v14b-rag-nudge-replay-benchmark
edges: []
---

tests/test_publication_lines.py держит класс «dev-machine path» (буква диска, двоеточие, каталог Work) на потолке 22 отслеживаемых файла и считает ТОЛЬКО отслеживаемые файлы (память #703): одна строка `task log` с абсолютным путём диска попадает в tausik/tasks/<slug>.md и после git add даёт 23 — лента красная. Журнал append-only: `task update --notes --notes-overwrite` переписывает tasks.notes, но проекция ## Journal строится из таблицы task_logs (scripts/state_export.py:_journal_section), так что это не помогает. Рабочий путь: `tausik redact --pattern "<путь>" --label dev-machine-path --reason "..."` (сначала dry-run, затем sqlite backup() БД и --apply), потом `tausik state export`. Маркер «[вычеркнуто: dev-machine-path]» остаётся в записи, оригинал не хранится нигде. То же относится к тексту памяти: запись, которая цитирует сам путь как пример, тоже считается вхождением — эта запись поэтому его не цитирует. Правило: в журналах и памяти называть worktree и каталоги относительно репозитория (../tausik-B), а не абсолютно.
