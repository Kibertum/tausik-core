---
slug: v1-5-is-not-published-yet-corrected-2026-06-14-v15p-release
task: v15p-release-150
date: "2026-06-14"
edges: []
---

## Decision

v1.5 is NOT published yet (corrected 2026-06-14); v15p-release-150 re-opened as the final publish gate. Scope = ALL remaining v15 work-streams + the previously-unleveled snippet & orchestrator features (now tagged [1.5]). v14c dashboard/web-catalog stay [DEFERRED 1.5]. RENAR (renar-adoption / [Unreleased]) is road-to-2.0, not a 1.5 blocker. v15-cross-ide-parity (AIDD) epic is empty → NEEDS plan-or-defer decision before release.

## Rationale

Framework misread 1.5 as shipped: release-150 (prep bump+CHANGELOG+docs) was closed and CHANGELOG carries 2026-06-13, but no tag/publish happened and the user gave no close command. Ordered execution: (1) v15-model-routing P1 phase-matrix→phase-surfaces, then P2 subagent-hints+routing-telemetry; (2) v15-snippet-system mcp-search+brain-integration; (3) v15-orchestrator-worker-pattern; (4) v15-polish: defect fix-bootstrap-diff-skill-warn, then P2 agents-md-bootstrap/coverage-badge/fts-optimize-cron + qa-enforce-ble001 (complex); (5) FINAL v15p-release-150: tag+push public+verify CHANGELOG date. Empty cross-ide-parity flagged, not padded with invented tasks.
