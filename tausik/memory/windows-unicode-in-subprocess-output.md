---
slug: windows-unicode-in-subprocess-output
title: "Windows Unicode in subprocess output"
type: gotcha
tags:
  - unicode
  - windows
task: null
edges: []
---

bootstrap.py uses print() with ASCII arrows (->) not Unicode (→) to avoid UnicodeEncodeError on Windows. sys.stdout.reconfigure(encoding=utf-8) in project.py entry point. Cross-platform: always use errors=replace for console output.
