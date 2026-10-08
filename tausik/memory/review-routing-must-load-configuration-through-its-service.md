---
slug: review-routing-must-load-configuration-through-its-service
title: "Review routing must load configuration through its service handle"
type: gotcha
tags:
  - config
  - multi-project
  - review
task: load-review-floor-configuration-from-the-service
edges: []
---

Task context and closure can execute with cwd pointing at another project. Pass svc.tausik_dir() into load_config and into review-route construction; a conflicting-cwd test must prove the target project's hard floor wins.
