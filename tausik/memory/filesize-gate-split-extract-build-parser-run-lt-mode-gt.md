---
slug: filesize-gate-split-extract-build-parser-run-lt-mode-gt
title: "Filesize gate split: extract build_parser + run_&lt;mode&gt;() into &lt;orig&gt;_modes.py"
type: pattern
tags:
  - argparse
  - filesize
  - refactor
  - split-pattern
task: v14b-followup-bootstrap-py-filesize-debt
edges: []
---

When an orchestrator file (CLI entrypoint with argparse + mode handlers) exceeds the 400-line gate, the cheapest split is to extract the argparse setup as `build_parser()` plus each mode handler (`run_dry_run()`, `run_refresh_mode()`, `run_post_bootstrap()`, etc.) into a sibling `&lt;orig&gt;_modes.py` module. The original file becomes a thin dispatcher: `args = build_parser().parse_args(); if args.dry_run: run_dry_run(...); return`.

Established this session by bootstrap.py 530→361 split into bootstrap.py + bootstrap_modes.py (253). Public CLI surface stayed identical because argparse object is constructed in build_parser(), not embedded in main().

Triggers: any file where main() body contains argparse setup AND ≥2 distinct mode paths (dry-run / refresh / init / etc.). Counter-pattern: files with single linear flow — split by helper extraction instead.
