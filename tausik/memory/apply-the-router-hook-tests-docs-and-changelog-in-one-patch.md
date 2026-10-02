---
slug: apply-the-router-hook-tests-docs-and-changelog-in-one-patch
title: "Apply the router, hook, tests, docs, and changelog in one patch"
type: dead_end
tags:
  - apply-patch
  - docs
  - routing
task: route-explanations-to-smallest-useful-format
edges: []
---

Approach: Apply the router, hook, tests, docs, and changelog in one patch
Reason: The RU configuration anchor differed by two words, so apply_patch correctly rejected the whole patch. Split code/tests from documentation and anchor the docs on their exact current text.
