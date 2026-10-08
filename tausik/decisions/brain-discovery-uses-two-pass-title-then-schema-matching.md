---
slug: brain-discovery-uses-two-pass-title-then-schema-matching
task: v14b-defect-brain-enable-no-discovery
date: "2026-05-06"
edges: []
---

## Decision

Brain discovery uses two-pass title-then-schema matching, NOT a new CLI subcommand. Schema-match is soft: required-property whitelist per category (presence + type), extras tolerated. Title-match wins (zero extra API calls in the happy path); schema-fallback only runs for unmatched categories.

## Rationale

Existing run_wizard --join-existing flow already had everything needed except the schema-fallback step. Adding a new `brain enable` subcommand would have duplicated that flow (DRY violation) and split documentation across two surfaces. Soft schema check means renaming a Notion column (extra meta) does not break discovery, while a wrong type in a required field still rejects (preventing brain from writing to an unrelated database). Two-pass with title-first preserves the canonical happy path's zero-overhead behavior.
