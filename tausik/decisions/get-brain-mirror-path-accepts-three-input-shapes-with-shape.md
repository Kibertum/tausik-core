---
slug: get-brain-mirror-path-accepts-three-input-shapes-with-shape
task: brain-review3-fixes
date: "2026-04-24"
edges: []
---

## Decision

get_brain_mirror_path accepts three input shapes with shape-detection, not a single-shape contract

## Rationale

Two working callers (service_knowledge.decide, brain_runtime.try_brain_write_*) had the already-merged brain dict in hand and passed it to a function that silently accepted the wrong shape — user's local_mirror_path was replaced with DEFAULT_BRAIN. Reviewed three options: (a) split into two functions, (b) require merged callers to pass None and re-read config, (c) shape-detect via "brain" key absence + merged-shape markers. Picked (c): keeps a single public name, zero caller friction, regression tests lock the contract for both shapes. Option (b) was the initial fix but left a landmine for the next caller; option (a) adds API surface and documentation burden.
