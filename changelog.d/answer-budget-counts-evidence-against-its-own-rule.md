<!-- lang: en -->
### Changed — the answer budget counts the retelling, not the proof

The answer measure counted every word, so quoting a failing test or a table of
measurements pushed an answer over budget — the rule said the budget is on the
retelling, and the measure did the opposite. Words inside closed fenced blocks and
markdown table rows now count as evidence (`evidence_words_median`) and are left out of
`final_words`. An unclosed fence exempts nothing. The ratchet baseline is declared anew
on the new measure: median 162, p90 365.

<!-- lang: ru -->
### Изменено — бюджет ответа считает пересказ, а не доказательство

Мера ответа считала каждое слово, поэтому цитата упавшего теста или таблица замеров
выталкивала ответ за бюджет, хотя правило ставит бюджет на пересказ. Теперь слова в
закрытых fenced-блоках и строках markdown-таблиц считаются доказательством
(`evidence_words_median`) и в `final_words` не входят. Незакрытый блок ничего не
освобождает. База храповика объявлена заново на новой мере: медиана 162, p90 365.
