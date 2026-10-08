---
slug: vendor-seo-frontmatter-fix-is-wiped-by-every-vendor
title: "vendor_seo frontmatter fix is wiped by every vendor redeploy — .kilo is untracked"
type: gotcha
tags:
  - "kilo,vendor,seo,frontmatter,redeploy"
task: reapply-kilo-vendor-seo-tools-as-object
edges: []
---

The 2026-10-06 fix converting .kilo/agents/vendor_seo/*.md frontmatter from a Claude Code comma string (tools: Read, Bash, Write, Grep) to Kilo's object form (tools: + lowercase boolean keys) was wiped by a later vendor bundle redeploy — all seven files regressed within hours (session #294 reapplied it as reapply-kilo-vendor-seo-tools-as-object; verify run #3551 exit=0 confirms the reapplied state was green, so the wipe and the recovery are both directly observed, not inferred). .kilo/ is gitignored by design, so git cannot protect these edits: any redeploy of the vendor bundle restores the broken spelling and Kilo again refuses to load the agents. If the error 'tools: Expected object | undefined, got ...' reappears, re-run the conversion (split the comma list, lowercase, emit a YAML block of <name>: true) instead of hunting a new cause. A durable fix needs the vendor bundle's source templates to ship the object form.
