---
slug: goloe-vx-y-v-dokumente-chitaetsya-version-ref-skanerom-kak
title: "Голое vX.Y в документе читается version-ref сканером как версия TAUSIK: имя чужого стандарта обязано стоять в 24 символах ПЕРЕД числом"
type: gotcha
tags:
  - doc-drift
  - docs
  - senar
  - version-ref
task: senar-version-claimed-in-three-places-disagrees
edges: []
---

doc_drift_common._is_foreign_version смотрит окно ровно в 24 символа ПЕРЕД совпадением и ищет там префикс из _FOREIGN_VERSION_PREFIXES (SENAR, Python, OWASP, RENAR). Если имя стандарта дальше — число считается версией TAUSIK и сверяется с constants.json tausik_version.

Поймано в смене #225 на СВОЁМ ЖЕ тексте: предложение «**v1.3 is the edition TAUSIK claims.**» дало `gen_doc_constants --check` две красные строки (README.md:185, README.ru.md:184) — «version ref 'v1.3' does not match tausik_version='1.8.0'». Лечится не подавлением, а порядком слов: «**TAUSIK claims SENAR v1.3 Core**» — имя стандарта вплотную перед числом.

Правило при написании любого текста о чужой версии: ставь имя стандарта НЕПОСРЕДСТВЕННО перед номером, а не в начало абзаца. Проверяется одной командой: `python scripts/gen_doc_constants.py --check`.
