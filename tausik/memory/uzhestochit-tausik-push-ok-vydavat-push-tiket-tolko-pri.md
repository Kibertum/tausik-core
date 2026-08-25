---
slug: uzhestochit-tausik-push-ok-vydavat-push-tiket-tolko-pri
title: "Ужесточить `tausik push-ok`: выдавать push-тикет только при наличии зелёного verify-receipt на текущ"
type: dead_end
tags:
  - push-gate
  - receipts
  - senar
  - verify
task: null
edges: []
---

Approach: Ужесточить `tausik push-ok`: выдавать push-тикет только при наличии зелёного verify-receipt на текущий HEAD — «нельзя запушить непроверенное» как механизм, а не привычка.
Reason: Requirement к сущности, которой нет. Таблица verification_runs ключуется по (task_slug, files_hash), колонки с commit sha в ней вообще нет: pragma table_info даёт [id, task_slug, scope, command, exit_code, summary, files_hash, ran_at, duration_ms, receipt_json]. Receipt внутри receipt_json привязан к HEAD на момент прогона, но кэш ищется не по нему.

Практическое следствие проверено на сегодняшнем релизе: verify гонялся на тиках веток, а push делался с merge-коммита af283bd, у которого своего receipt нет и быть не могло. Такой гейт заблокировал бы ровно тот релиз, ради качества которого затевался, и первым же действием его обошли бы через опцию отключения — то есть он не добавил бы принуждения, а добавил бы привычку его обходить.

Чтобы идея заработала, сначала нужна модель «verify привязан к коммиту, а не к набору файлов», и ответ на вопрос, что считать проверенным для merge-коммита (наследовать receipt родителя? требовать прогон после мержа?). Это отдельное архитектурное решение, а не ужесточение флага.
