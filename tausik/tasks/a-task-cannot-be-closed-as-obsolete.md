---
slug: a-task-cannot-be-closed-as-obsolete
title: "A task cannot be closed as obsolete or won't-do: the lifecycle has done, blocked and delete, and nothing for a finding that time resolved"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-architecture-and-research
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Session #265: the owner asked to close four obsolete tasks. The lifecycle offered three exits and none fit: task done demands per-criterion ✓ evidence (a FAIL line blocks, 'not exercised' is not recognised), task delete erases the record and its journal, and leaving them open lies to the roadmap. The honest closure took writing acceptance criteria after the fact for two tasks that reality had satisfied, and a hard delete for a duplicate. Add a fourth exit — obsolete / won't do — that keeps the record, requires a reason, stops counting the task as open in the map, and is reported apart from done (a closed finding is not a shipped one).

## Acceptance Criteria

## Plan

## Rollback

git revert; a status value and its readers

## Journal
