---
slug: env-parser-space-before-equals-breaks-token-resolution
title: ".env parser space-before-equals breaks token resolution"
type: gotcha
tags:
  - brain
  - env
  - parser
task: null
edges: []
---

.tausik/.env was generated with `NOTION_TAUSIK_TOKEN =value` (space before =). Brain CLI couldn't resolve the env var even though token was present (50 chars). Standard .env parsers reject keys with trailing whitespace. Fix: sed -i 's/^NOTION_TAUSIK_TOKEN  *= */NOTION_TAUSIK_TOKEN=/' .tausik/.env. Bootstrap should generate .env without space, OR brain_runtime should strip whitespace from keys when parsing. File a tracking issue under tausik repo for next polish round.
