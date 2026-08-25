---
slug: cursorrules-is-preserve-on-exists-in-generate-cursorrules
title: ".cursorrules is preserve-on-exists in generate_cursorrules"
type: gotcha
tags: []
task: null
edges: []
---

`bootstrap/bootstrap_generate.py::generate_cursorrules` writes the file only when it doesn't exist (`if not os.path.exists(path): open(path, 'w')...`). So editing the bootstrap template won't propagate to a project that already has a `.cursorrules` — re-running bootstrap looks like it succeeded ("Will generate: .cursorrules") but the file is stale.

Workaround during a refactor: delete `.cursorrules` before re-bootstrapping, or accept that gitignored stale local files don't affect AC #5 ("regenerated cleanly from harness/") which is satisfied for fresh projects.

Same preserve-on-exists semantics may apply to other generators in `bootstrap_generate.py` — verify before assuming a regen will refresh a target.</content>
<parameter name="tags">["bootstrap", "cursorrules", "regen", "preserve-on-exists"]
