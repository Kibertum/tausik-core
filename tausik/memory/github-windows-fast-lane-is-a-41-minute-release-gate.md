---
slug: github-windows-fast-lane-is-a-41-minute-release-gate
title: "GitHub Windows fast lane is a 41-minute release gate"
type: gotcha
tags:
  - ci
  - economy
  - release
  - tests
  - windows
task: null
edges: []
---

GitHub Actions run 37038485265 measured the Windows 3.12 fast lane at about 41 minutes while Ubuntu full finished in 7 minutes and macOS fast in 9. The workflow comment still says ~5 minutes. A 1.11.x follow-up should measure node distribution and select only Windows-sensitive coverage without weakening the Ubuntu full lane or platform-specific behavior.
