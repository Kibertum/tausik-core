---
slug: detect-a-swallowed-tool-call-by-structure-closing-tag-next
title: "Detect a swallowed tool call by STRUCTURE (closing tag + next parameter/invocation), not by any tag"
type: pattern
tags: []
task: tool-call-syntax-leaks-into-entity-text
edges: []
---

Session #272: the loose 'any <parameter>/</field> tag' signature flagged the card that described the defect; the structural signature </X> followed by <parameter name= / </invoke> / <invoke name= / <tag"?> flagged exactly the 64 corrupted entities and 0 prose. Guard lives in SQLiteBackend._run_write + _update. Repair: cut from the signature; in append-only journals cut only up to the next '[20' entry; recover lost empty columns from <parameter name=X>VALUE in the tail.
