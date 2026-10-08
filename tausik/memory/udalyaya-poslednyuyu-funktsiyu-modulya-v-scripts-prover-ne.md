---
slug: udalyaya-poslednyuyu-funktsiyu-modulya-v-scripts-prover-ne
title: "Удаляя последнюю функцию модуля в scripts/, проверь, не унёс ли ты вместе с ней блок `if __name__ == \"__main__\": refuse_direct_run`"
type: gotcha
tags:
  - guards
  - refactoring
  - scripts
task: mcp-verify-is-a-second-command-not-a-second-rendering
edges: []
---

Вынес четыре приватных печатника из project_cli_verify.py в общий рендерер, вырезав их регуляркой «от def до следующего def или конца файла». Последняя вырезка забрала и хвост файла — охранный блок refuse_direct_run. Модуль стал молча выходить с кодом 0 при прямом запуске, а «молчание читается как успех» — ровно то, ради чего охрана заведена. Поймал tests/test_cli_entrypoint_guard.py, параметризованный по всем scripts/project_cli*.py. Вырезая функции скриптом, ВСЕГДА смотри `tail` файла после правки.
