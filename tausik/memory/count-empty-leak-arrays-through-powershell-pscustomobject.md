---
slug: count-empty-leak-arrays-through-powershell-pscustomobject
title: "Count empty leak arrays through PowerShell PSCustomObject aggregation"
type: dead_end
tags: []
task: validate-the-final-1-11-release-candidate
edges: []
---

Approach: Count empty leak arrays through PowerShell PSCustomObject aggregation
Reason: ConvertFrom-Json plus pipeline array coercion produced a non-zero aggregate even though the JSON report showed all three leak arrays empty; validate each named property explicitly instead
