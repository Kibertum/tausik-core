---
slug: path-classifiers-must-lowercase-normalize-on-case
title: "Path classifiers must lowercase-normalize on case-insensitive filesystems"
type: gotcha
tags:
  - case-sensitivity
  - path-classifier
  - security
  - v1.4-polish
  - windows
task: v14b-defect-security-pattern-case-insensitive
edges: []
---

`is_security_sensitive` was case-sensitive on path tokens, basenames, and extensions. PascalCase auth dirs (`OAuth/`, `Payments/`, `Auth.py`) and uppercase credential extensions (`keys.PEM`, `id_rsa.KEY`) all bypassed the classifier — exactly what the v14b-defect-qg2-security-substring-too-broad rewrite was meant to prevent. On Windows/macOS the FS is case-insensitive so `keys.PEM` and `keys.pem` are the same file, but our classifier treated them as different.

Fix: lowercase the normalized path once (`norm = "/" + raw.replace("\\","/").lstrip("/").lower()`) before any token/basename/extension match. Token/basename/extension sets are already lowercase by convention.

Apply this pattern to any other path-based classifier (e.g. gate_runner._FILESIZE_EXEMPT_DIRS — review found the same smell there as M3, deferred).
