---
slug: doctor-accepts-trimmed-claude-md-baseline-via-heuristic-not
task: clean-tausik-doctor-warnings-brain-enabled-false-c
date: "2026-05-06"
edges: []
---

## Decision

Doctor accepts trimmed CLAUDE.md baseline via heuristic, not config flag

## Rationale

Two cheap signals (file <6KB AND ## Reference body links to docs/{ru,en}/agent-contract.md) are objective enough to identify the v1.4-polish trim without requiring a per-project opt-in. Avoids config schema growth and a manual user step. Heuristic runs early in _check_claudemd_drift so trimmed projects don't fall through to None on missing bootstrap_templates path.
