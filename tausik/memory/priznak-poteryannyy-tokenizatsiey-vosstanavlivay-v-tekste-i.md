---
slug: priznak-poteryannyy-tokenizatsiey-vosstanavlivay-v-tekste-i
title: "Признак, потерянный токенизацией, восстанавливай в тексте — и это уже ТРЕТИЙ модуль подряд"
type: pattern
tags: []
task: write-gate-does-not-treat-a-newline-as-a-command-separator
edges: []
---

python_invocation.py (#203), shell_redirection.py (#204), shell_statements.py (#205) — один и тот же ход: shlex уничтожает признак (форму запуска, склейку номера дескриптора, перевод строки), поэтому его читают в ИСХОДНОМ ТЕКСТЕ до токенизации, отдельным измеримым модулем с матрицей. Признак ход исчерпал себя не как совпадение, а как правило: если разбор гейта опирается на shlex, СНАЧАЛА спроси, что shlex выбрасывает, и ищи там объявленное-но-мёртвое.
