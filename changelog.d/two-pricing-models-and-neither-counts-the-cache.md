<!-- lang: en -->
### Fixed — the cost model was blind to 94% of the bill

Rates lived in two places that could not answer together. `cost_pricing` ships a table
of input and output, prices no cache at all, and is what writes `usage_events.cost_usd`.
`token_price` understands cache but read rates only from a config nobody had filled, so
the cache-aware report printed UNPRICED. One path counted the small stream; the other
could see the large one and had no rate for it.

Measured over the last ten sessions: **3,044,531,708 cached tokens read against
3,922,523 of output — 776 times as many.** Priced, that is **cache 94.2% of the bill,
output 5.8%**.

`token_price` now falls back to the shipped table, deriving the cache rates from the
input rate by the published multipliers (read 0.1x, write 1.25x) rather than carrying a
second table that would drift. A project's own `token_price` entry still overrides it
whole, so the config predicts the bill from what is written in it.

**A DATE SUFFIX NO LONGER UNPRICES A MODEL.** `claude-haiku-4-5-20251001` is the id this
host reports and the table is keyed without the date, so the canonical Haiku went
unpriced; trailing numeric segments are now dropped until something matches. That alone
brought 984 previously uncounted calls into the total.

The report states the cache share in one line, because reading the rows alone is what
led this project's own author to announce that output was the bill.

<!-- lang: ru -->
### Исправлено — модель цены не видела 94% счёта

Ставки жили в двух местах, которые не могли ответить вместе. `cost_pricing` несёт
таблицу входа и выхода, кэш не оценивает вовсе и именно он пишет
`usage_events.cost_usd`. `token_price` умеет кэш, но брал ставки только из конфига,
которого никто не заполнил, — и кэш-осведомлённый отчёт печатал UNPRICED. Один путь
считал малый поток; другой видел большой и не имел для него ставки.

Замер по последним десяти сменам: **3 044 531 708 прочитанных из кэша токенов против
3 922 523 выхода — в 776 раз больше.** В деньгах это **кэш 94,2% счёта, выход 5,8%**.

`token_price` падает теперь на встроенную таблицу и выводит кэшевые ставки из входной
по опубликованным множителям (чтение 0,1x, запись 1,25x), а не заводит вторую таблицу,
которая разойдётся. Запись проекта в `token_price` по-прежнему перебивает встроенную
целиком: по конфигу видно, каким будет счёт.

**СУФФИКС С ДАТОЙ БОЛЬШЕ НЕ ЛИШАЕТ МОДЕЛЬ ЦЕНЫ.** `claude-haiku-4-5-20251001` — тот id,
который сообщает хост, а таблица ключуется без даты, поэтому канонический Haiku не
оценивался; хвостовые числовые сегменты теперь отбрасываются до совпадения. Одно это
вернуло в счёт 984 ранее не учтённых вызова.

Отчёт называет долю кэша отдельной строкой: чтение одних только строк — ровно то, из-за
чего автор этого проекта объявил счётом выход.
