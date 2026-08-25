---
slug: check-docs-version-ref-scanner-flags-vx-y-in-claude-md-auto
title: "check_docs version-ref scanner flags vX.Y in CLAUDE.md auto-gen memory-tail"
type: gotcha
tags: []
task: check-docs-version-ref-treat-renar-as-foreign-vers
edges: []
---

scan_version_refs (doc_drift_scanners.py) checks every vX.Y in CROSS_FILE_SCAN_TARGETS incl. CLAUDE.md against tausik_version. The auto-generated memory-tail can cite external-spec versions (e.g. 'renar.tech v1.0-draft' from decision #103) → false-positive drift that blocks ALL commits (pre-existing red from session #87). Sibling specs version independently: add them to _FOREIGN_VERSION_PREFIXES (now SENAR/Python/OWASP/RENAR/renar; 24-char lookbehind). When a new spec version is cited in decisions, add its prefix here.
