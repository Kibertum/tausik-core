---
slug: mixin-private-helpers-collide-silently-across-multiple
title: "Mixin private helpers collide silently across multiple inheritance (MRO shadows, no error)"
type: gotcha
tags: []
task: null
edges: []
---

ProjectService/SQLiteBackend compose many *Mixin classes via multiple inheritance sharing ONE flat method namespace. Two mixins defining the same "private" helper name (e.g. `_require_draft`, `_canonical_body`, `_architect_sign`) silently collide: Python MRO resolves `self._helper()` to whichever mixin is listed FIRST in the class bases, with zero error or warning. Found when ActzMixin was added alongside AdaptsMixin: both defined `_canonical_body`/`_architect_sign`/`_require_draft`, and ACTZ's signing calls silently ran ADAPT's version (would have signed the wrong payload against the wrong table). Tests caught it immediately as "ADAPT 'z1' not found" errors, but a less-obvious case could pass tests while signing/validating against the wrong data. Fix: prefix EVERY private helper in a new RENAR-artifact mixin with the entity name (e.g. `_actz_require_draft`, `_actz_canonical_body`) rather than reusing the generic name ADAPT's mixin already claims. Before adding a new mixin method starting with `_`, grep the other mixins mixed into the same composed class for the same name first.
