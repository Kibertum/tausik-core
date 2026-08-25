---
slug: skill-repos-use-shallow-clone-git-clone-depth-1-not
task: skill-install-system
date: "2026-04-07"
edges: []
---

## Decision

Skill repos use shallow clone (git clone --depth 1) not submodules — .tausik/ is gitignored so submodules won't work

## Rationale

.tausik/ is in .gitignore, submodules require .gitmodules tracked by git. Shallow clone gives same result without git overhead.
