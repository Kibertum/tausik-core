---
slug: zero-external-dependencies
title: "Zero external dependencies"
type: convention
tags:
  - dependencies
  - stdlib
task: null
edges: []
---

Frai core uses only Python stdlib (sqlite3, json, os, re, datetime, argparse). No pip packages in runtime. Only dev dependency: pytest in .frai/venv/. This is a deliberate design choice for portability — framework ships as plain .py files via bootstrap.
