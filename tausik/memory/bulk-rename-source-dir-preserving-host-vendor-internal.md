---
slug: bulk-rename-source-dir-preserving-host-vendor-internal
title: "Bulk-rename source dir preserving host + vendor + internal namespaces"
type: pattern
tags: []
task: v14b-rename-harness
edges: []
---

When renaming a source directory like `agents/` → `harness/` across the repo, **never** do a blind global find-replace. Use placeholder substitution to protect three classes of references that look identical to the source path but mean something different:

1. **Host namespaces** — `.claude/agents/`, `.codex/agents/`, `.cursor/agents/`, `.qwen/agents/`. These are the IDE host's own directories (Claude Code's native sub-agent folder, Codex CLI's, etc.). Renaming them silently breaks integrations.
2. **Vendor namespaces** — `agents/` inside vendor skill tarballs (and the matching `agents_dir` parameter, `counts["agents"]` dict key in bootstrap_vendor.py). Vendor packs install INTO the host's `.claude/agents/`, so the vendor concept stays bound to the host name.
3. **Internal subfolders** — e.g. `harness/skills/review/agents/<name>.md` (parallel-reviewer instructions inside the `/review` skill). The literal "agents" inside a renamed tree is intentional.

Implementation skeleton (Python):
```python
PROTECTED = (".claude/agents/", ".codex/agents/", ".cursor/agents/", ".qwen/agents/",
             "skills/review/agents/")
PLACEHOLDERS = tuple(f"\x00P{i}\x00" for i in range(len(PROTECTED)))
def rewrite(text):
    for p, ph in zip(PROTECTED, PLACEHOLDERS): text = text.replace(p, ph)
    text = text.replace("agents/", "harness/")
    for p, ph in zip(PROTECTED, PLACEHOLDERS): text = text.replace(ph, p)
    return text
```

Two passes are needed: first `agents/` (with slash) for path strings, then `"agents"` and `'agents'` for separate string literals in `os.path.join(..., "agents", ...)` patterns. Skip `bootstrap_vendor.py` entirely since every reference there is the host/vendor concept.

Verify with `git ls-files | xargs grep` on tracked files only (gitignored generated outputs like `.cursorrules` are stale until bootstrap-overwrite, but bootstrap may PRESERVE them — `generate_cursorrules` checks `if not os.path.exists(path)` before writing).</content>
<parameter name="tags">["rename", "refactor", "namespace", "find-replace", "v1.4-polish"]
