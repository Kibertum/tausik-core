---
slug: edit-tool-s-string-match-dlya-sliyaniya-testov
title: "Edit tool с string-match для слияния тестов содержащих невидимые Unicode separators (U+2028, U+2029,"
type: dead_end
tags:
  - edit-tool
  - parametrize
  - tests
  - unicode
task: v14c-mass-parametrize-batch-1
edges: []
---

Approach: Edit tool с string-match для слияния тестов содержащих невидимые Unicode separators (U+2028, U+2029, U+0085) в test bodies (например test_u2028_line_separator_does_NOT_trigger_bypass в test_hooks_common.py)
Reason: Edit пытается escape-swap fallback (документировано в его error message), но не сохраняет точные байты невидимых Unicode separators. old_string с visible-ASCII представлением "hook said confirm: cross-project right?" не матчит реальный байт-набор файла где есть   между словами. Workaround: byte-aware Python script через `re.sub` на content прочитанном с encoding='utf-8' — Python's str preserves bytes correctly через round-trip. Применил в G8+G18 merge (12 tests → 1 parametrize), test passes 33/33.
