---
slug: ast-clone-signature-never-flatten-list-valued-ast-fields-to
title: "AST clone signature: never flatten list-valued AST fields to a scalar placeholder"
type: gotcha
tags: []
task: v15-snippet-ast-detect
edges: []
---

snippet_detect._NAME_FIELDS maps scalar identifier fields (Name.id, arg.arg, etc.) to placeholders for type-2 clone normalization. Global.names/Nonlocal.names are list[str], NOT scalar — mapping them to one token ('GLOBAL') collapsed 'global a' and 'global x,y' to the same signature → false-positive clusters (tausik-reviewer CRIT). Fix: leave list fields out of _NAME_FIELDS so _dump recurses into the list, preserving arity. Rule: only scalar identifier fields get placeholder-flattened; list fields must recurse.
