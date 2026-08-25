---
slug: serviceerror-for-business-logic-errors
title: "ServiceError for business logic errors"
type: convention
tags:
  - errors
  - exceptions
task: null
edges: []
---

All business logic errors use ServiceError (from frai_utils). ValueError only for pure input validation (slug format, field length). CLI catches ServiceError and prints to stderr with exit 1. Never swallow exceptions silently — always raise or log.
