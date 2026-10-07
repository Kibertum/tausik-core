---
slug: duplicating-the-force-retired-unblock-test-in-both-test
title: "Duplicating the force-retired unblock test in both test_session_capacity.py and test_session_signal_"
type: dead_end
tags: []
task: blocked-is-a-status-without-a-question-to-unblock-it
edges: []
---

Approach: Duplicating the force-retired unblock test in both test_session_capacity.py and test_session_signal_not_gate.py
Reason: After the v77 edit both copies got a docstring and the same TypeError shape, so the AST signature merged them into a new dedupe group: 283/671 vs ratchet 282/669. Fix: keep one copy in the signal file whose module docstring owns the retired-flag side; capacity file keeps a pointer comment
