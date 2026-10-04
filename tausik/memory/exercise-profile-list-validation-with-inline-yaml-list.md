---
slug: exercise-profile-list-validation-with-inline-yaml-list
title: "Exercise profile-list validation with inline YAML list syntax in state-import tests."
type: dead_end
tags: []
task: validate-assurance-metadata-at-state-import
edges: []
---

Approach: Exercise profile-list validation with inline YAML list syntax in state-import tests.
Reason: The state projection intentionally supports a restricted emitter dialect: lists are block-YAML and impact is a quoted JSON scalar. Tests must use the canonical emitted syntax or they test an unsupported parser.
