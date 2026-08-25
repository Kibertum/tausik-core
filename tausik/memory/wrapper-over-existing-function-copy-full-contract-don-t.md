---
slug: wrapper-over-existing-function-copy-full-contract-don-t
title: "Wrapper over existing function: copy full contract, don't guess"
type: convention
tags:
  - python
  - testing
  - wrappers
task: null
edges: []
---

Когда пишешь helper-wrapper над существующей функцией (напр. try_brain_write_decision над store_record), ОБЯЗАТЕЛЬНО открой source-of-contract (brain_mcp_write.py) и скопируй EVERY возможный status/return shape. Не угадывай по именам. Пример провала: try_brain_write_decision классифицировал только status='ok' как success, пропустил ok_not_mirrored (Notion ok + local mirror failed) → двойная запись в prod. Второй провал в том же файле: scrub_blocked возвращает issues как list[dict] с {detector,match,hint} keys, я писал как если бы это был list[str] → TypeError, swallowed by outer except, "exception: sequence item 0..." вместо scrub_blocked reason. Правило: открывай source файл, копируй полный mapping, добавляй тесты для КАЖДОГО варианта status.
