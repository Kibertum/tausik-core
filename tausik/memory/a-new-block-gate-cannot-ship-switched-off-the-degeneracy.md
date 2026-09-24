---
slug: a-new-block-gate-cannot-ship-switched-off-the-degeneracy
title: "A new block gate cannot ship switched off: the degeneracy audit reads enabled=false as silence"
type: gotcha
tags: []
task: changed-path-does-not-require-its-artifact-to-move
edges: []
---

Session #272 (path_artifact): a GateSpec with severity block and enabled false is a DISABLED debt in gate_degeneracy (universal gates only; stack-scoped ones are dormant). For an opt-in rule, ship it enabled with an empty rule set that returns NOT_APPLICABLE with a reason, plus a red_proofs entry and an EXCUSED/catch entry.
