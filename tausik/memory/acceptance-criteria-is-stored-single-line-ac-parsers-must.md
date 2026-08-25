---
slug: acceptance-criteria-is-stored-single-line-ac-parsers-must
title: "acceptance_criteria is stored single-line — AC parsers must be inline-aware"
type: gotcha
tags:
  - ac-evidence
  - parser
  - qg2
  - senar-rule5
task: fix-ac-evidence-parser-inline-numbered-single-line
edges: []
---

Tasks store acceptance_criteria as ONE line ('1. foo 2. bar 3. baz'), not newline-separated (confirmed across 40 real tasks: all nl=0). Any code that parses AC must NOT rely on line-anchored regex (^\\d+[.)] with re.MULTILINE collapses to 1 item). Use service_ac_evidence.parse_ac_text, which falls back to _split_inline_numbered (run-anchored on 1,2,3,… so stray numbers like 'Decision #138', 'returns 0', 'Python 3.11' don't inflate). Likewise, evidence-marker counting must go through build_report (recognises canonical 'AC-N: ✓'), NOT a bespoke r'\\d+[.)].*✓' regex — that was the bug producing 'N AC criteria, but only 0 markers' on every well-evidenced close. Fixed in fix-ac-evidence-parser-inline-numbered-single-line.
