---
slug: first-controlled-prose-focused-test-run
title: "First controlled-prose focused test run"
type: dead_end
tags:
  - answer-shape
  - tests
  - windows
task: controlled-prose-for-user-facing-answers
edges: []
---

Approach: First controlled-prose focused test run
Reason: Four assertions encoded legacy wording or platform-default encoding: exact ceiling 776, literal 'closing' and 'keep full', and cp1252 fixture output. The product contract is valid; rebase the ceiling to 773, assert equivalent semantics, and write the fixture as UTF-8.
