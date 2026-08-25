---
slug: negation-aware-keyword-detector-for-ac-validation
title: "Negation-aware keyword detector for AC validation"
type: pattern
tags:
  - linguistics
  - negation
  - qg-0
  - regex
  - validation
task: med-batch-2-qg
edges: []
---

When implementing keyword-based validation of free-form text fields (acceptance_criteria, notes, comments), substring match (`kw in text`) accepts negated forms as positives. "Works without errors" satisfies a "must mention errors" gate even though it's the OPPOSITE of articulating an error scenario. Robust pattern: (1) split text into per-criterion lines (handle both newline and inline numbering like "1. ... 2. ..."), (2) compile a negation-redaction regex matching "no", "without", "never", "нет", "без", etc. + their ~60-char span up to next sentence boundary, (3) substitute negation spans with whitespace, then (4) search for word-boundary-anchored keywords in the surviving text. Regex shape: `\b(?:no|without|нет|без|никогда|не\s+должно?\s+быть)\b[^.;\n]{0,60}` for redaction; `(?<![\w])(?:keyword1|keyword2|...)` for word-boundary keyword match (Cyrillic doesn't have proper \b but `(?<![\w])` works as a left-side anchor). Used in scripts/gate_negative_scenario.py for QG-0 negative-scenario detection. Same pattern applies anywhere a "must mention X" check could be defeated by "without X" / "no X" phrasing.
