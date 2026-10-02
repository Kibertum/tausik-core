---
slug: first-scoped-verify-after-compressing-the-answer-contract
title: "First scoped verify after compressing the answer contract"
type: dead_end
tags:
  - behavior
  - dedupe
  - tests
task: controlled-prose-for-user-facing-answers
edges: []
---

Approach: First scoped verify after compressing the answer contract
Reason: Two tests asserted the legacy English spellings 'two minutes' and 'one tangent, once'. The new contract preserves both behaviors as '≤2 min' and 'tangent last'. Replace wording assertions with semantic alternatives and collapse six identical nodes into one contract check.
