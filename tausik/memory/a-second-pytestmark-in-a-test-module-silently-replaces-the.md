---
slug: a-second-pytestmark-in-a-test-module-silently-replaces-the
title: "A second 'pytestmark =' in a test module silently replaces the first: dormancy and slow marks must be ONE list"
type: gotcha
tags:
  - "pytest,pytestmark,snapshot,dormancy"
task: null
edges: []
---

Session #260: tests/test_ci_lanes_are_honest.py got pytestmark = skipif(IS_PUBLIC_SNAPSHOT) at line 33 and already had pytestmark = pytest.mark.slow at line 48; the second assignment won, the dormancy mark vanished without a warning, and the built public snapshot ran the file against a .gitlab-ci.yml it does not carry (7 failures found only by running the snapshot's own lane). Rule: pytestmark = [mark, mark]; and a claim 'dormant on the snapshot' is proven only by a lane on a snapshot checkout with an EMPTY .tausik (the earlier 10522/21 run had a live DB beside it and hid this).
