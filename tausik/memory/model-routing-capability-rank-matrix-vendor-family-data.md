---
slug: model-routing-capability-rank-matrix-vendor-family-data
title: "Model routing = capability-rank matrix × vendor-family data"
type: pattern
tags:
  - glm
  - model-routing
  - providers
  - v155
  - zai
task: v155-model-profiles-data
edges: []
---

To support non-Claude models (z.ai GLM) without code-per-model, routing is split on two axes (Decision #119). The phase×complexity MATRIX (model_routing_matrix._MATRIX) emits an ABSTRACT capability rank (haiku/sonnet/opus/fable = 0..3, lowest→flagship). The concrete model id filling a rank is DATA per vendor family in model_profiles.DEFAULT_FAMILIES (overridable via .tausik/config.json model_profiles.families). suggest_model(..., family=) resolves rank→model for that family; family=None defaults to claude (back-compat, all existing tests unchanged). Banner infers family from the active model via model_profiles.vendor_of (glm-*→glm), falls back to model_profiles.default_family then claude. KEY GOTCHA: one model can fill several ranks (a single flagship GLM), so reverse_index picks the HIGHEST rank, AND the banner short-circuits to '✓ model match' when normalized(active)==normalized(rec_id) — without that, recommending an opus-rank model while running the same model that also fills fable-rank reads as false 'quality surplus'. _model_tier(id, families=) consults the reverse index so GLM ids get a rank (else None=unknown). Adding a new GLM model = edit config/DEFAULT_FAMILIES dict, no logic change.
