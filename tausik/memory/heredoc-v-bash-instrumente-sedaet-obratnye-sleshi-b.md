---
slug: heredoc-v-bash-instrumente-sedaet-obratnye-sleshi-b
title: "Heredoc в Bash-инструменте съедает обратные слэши: `\\\\b` → backspace, `\\\\n` → перевод строки внутри Python-литерала"
type: gotcha
tags:
  - bash
  - escaping
  - heredoc
  - windows
task: null
edges: []
---

Смена #254, три раза подряд: правки regex/f-строк через `python - <<'PY' … PY` записывали в файл ^H вместо `\b` и настоящий перевод строки вместо `\n` (ruff: «f-string: unterminated string»). Кавычки `'PY'` не спасают — раскрытие идёт до heredoc. Обходы: (1) писать патч-скрипт файлом через Write, затем `python patch.py`; (2) собирать escape через `chr(92)` внутри Python; (3) использовать Edit на файле. Одиночный `\\` (как в `path.replace("\\", "/")`) переживает, двойные последовательности перед буквой — нет. Правило: после любой heredoc-правки с обратными слэшами — `cat -A | grep '\^H'` и ruff.
