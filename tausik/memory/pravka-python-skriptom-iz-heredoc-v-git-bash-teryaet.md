---
slug: pravka-python-skriptom-iz-heredoc-v-git-bash-teryaet
title: "Правка Python-скриптом из heredoc в Git Bash теряет экранирование \\n"
type: gotcha
tags:
  - "windows,bash,heredoc,editing"
task: null
edges: []
---

Смена #267: трижды строка вида split("\n") или f"\n{x}", вписанная в файл через python - <<'EOF' ... EOF из Bash-инструмента, легла в файл НАСТОЯЩИМ переводом строки и сломала синтаксис (project_cli_review.py, project_cli_publish.py, test_metric_methods.py). Один раз сломанный файл попал под идущий фоновый verify-пакет и уронил чужую задачу. Как делать: правки с обратными слэшами — инструментом Edit/Write или скриптом-файлом, записанным Write в scratchpad и запущенным python <путь>; после любой правки скриптом — ruff check до следующего шага.
