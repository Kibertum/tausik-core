---
slug: encode-nested-assurance-json-as-a-single-quoted-yaml-scalar
title: "Encode nested assurance JSON as a single-quoted YAML scalar in the state-import regression"
type: dead_end
tags: []
task: validate-assurance-impact-enum-types
edges: []
---

Approach: Encode nested assurance JSON as a single-quoted YAML scalar in the state-import regression
Reason: The restricted canonical state parser accepts the emitter dialect, which uses a double-quoted scalar with escaped JSON quotes; the first fixture correctly failed as invalid JSON rather than reaching enum validation.
