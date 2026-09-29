<!-- lang: en -->
### Fixed — `metrics answers` and its ratchet read the oldest transcripts, not the newest

The transcript list is oldest-first and both readers took its first N entries, so the
"last ten transcripts" were the project's first ten, and the measure could never move.
On the newest ten: 238 answers, median 198 words, p90 453 (the frozen window said 430
and 1325). The ratchet baseline is re-measured on the corrected window.

<!-- lang: ru -->
### Исправлено — `metrics answers` и его храповик читали самые старые транскрипты

Список транскриптов упорядочен от старых к новым, и оба читателя брали его первые N
записей: «последние десять транскриптов» были первыми десятью в истории проекта, и мера
не могла сдвинуться. На новейших десяти: 238 ответов, медиана 198 слов, p90 453 (застывшее
окно показывало 430 и 1325). База храповика перемерена на исправленном окне.
