---
slug: co-locate-message-text-with-its-data-module-near-filesize
title: "Co-locate message text with its data module near filesize cap"
type: convention
tags: []
task: null
edges: []
---

When a file approaches the 400-line filesize cap, move user-facing MESSAGE TEXT (nag/block strings, templates) into the data module it describes (e.g. Rule-7 messages -> root_cause.py next to ROOT_CAUSE_CATEGORIES). Wins: (1) message can't drift from the data/parser it quotes; (2) the large orchestration module (service_task_done.py) stays under cap. Used in rule7-rootcause-nag-inline-template.
