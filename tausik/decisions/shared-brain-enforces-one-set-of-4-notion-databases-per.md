---
slug: shared-brain-enforces-one-set-of-4-notion-databases-per
task: v133-impl
date: "2026-04-28"
edges: []
---

## Decision

Shared Brain enforces ONE set of 4 Notion databases per workspace, shared by all projects; per-project privacy via Source Project Hash column, NOT separate DB sets. v1.3.3 brain_init wizard now structurally refuses to create duplicates: pre-flight Notion search for canonical titles, full match → refuse + suggest --join-existing; partial match → refuse (ambiguous); --force-create as audit-logged escape hatch.

## Rationale

Real incident: agent in LegalOS project ran plain `brain init`, created a parallel set of 4 BRAIN DBs in same Notion workspace, then rationalized the duplicates as "per-project DBs for privacy" — exact opposite of design. Documentation alone doesn't prevent agent hallucination; the wizard had to refuse the action structurally. Architecture choice (one-set-per-workspace) was implicit before, now explicit in code, SKILL.md, and shared-brain.md docs.
