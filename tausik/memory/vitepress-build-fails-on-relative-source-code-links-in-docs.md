---
slug: vitepress-build-fails-on-relative-source-code-links-in-docs
title: "VitePress build fails on relative source-code links in docs/*.md"
type: gotcha
tags:
  - build
  - dead-link
  - docs
  - site
  - vitepress
task: v15-site-redesign
edges: []
---

A docs/*.md link like [x](../../tests/foo.py) makes `pnpm build` in site/ fail with "dead link" (ignoreDeadLinks:false) — the synced site has no tests/ tree. Source-code refs MUST use the GitHub-blob form: https://github.com/Kibertum/tausik-core/blob/main/<path>. Cross-file doc refs stay relative within the same locale. config.ts lines 14-16 document this; the receipts-docs work (session #81) shipped 2 such broken links in no-sdk-verify.md (EN+RU) that only surfaced when site rebuilt in session #82. Note: HomeLanding.vue is NOT in CROSS_FILE_SCAN_TARGETS, so stale version/count text there does NOT trip gen_doc_constants --check — only the 8 scanned files (README*, AGENTS.md, CLAUDE.md, docs/{en,ru}/{architecture,mcp}.md) do.
