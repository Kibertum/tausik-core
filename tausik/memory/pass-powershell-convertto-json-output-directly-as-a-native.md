---
slug: pass-powershell-convertto-json-output-directly-as-a-native
title: "Pass PowerShell ConvertTo-Json output directly as a native CLI argument"
type: dead_end
tags: []
task: public-snapshot-tests-read-excluded-files
edges: []
---

Approach: Pass PowerShell ConvertTo-Json output directly as a native CLI argument
Reason: Windows native argument parsing stripped JSON quotes before project.py. Invoke project.py through Python subprocess with an argv list.
