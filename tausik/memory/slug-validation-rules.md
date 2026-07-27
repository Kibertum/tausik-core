---
slug: slug-validation-rules
title: "Slug validation rules"
type: convention
tags:
  - slugs
  - validation
task: null
edges: []
---

Slugs must match ^[a-z0-9][a-z0-9-]*$ (lowercase, digits, hyphens, starts with alphanumeric). Validated by frai_utils.validate_slug(). Used for epics, stories, tasks, plans. Title max 512 chars (validate_length), content max 100000 chars (validate_content).
