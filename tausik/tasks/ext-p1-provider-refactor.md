---
slug: ext-p1-provider-refactor
title: "[ext P1] Framework extension-ready: provider-abstraction refactor (G3/G4)"
status: planning
epic: vscode-extension
story: ext-program
complexity: null
role: developer
stack: null
tier: substantial
call_budget: null
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

Make the framework extension-ready before building the extension. G3: route all IDE artifact generation through provider.generate_settings()/generate_commands() instead of the if ide== ladder in bootstrap.py (finish the unfinished v155 refactor). G4: collapse the four unsynchronized IDE registries (IDE_DIRS / ide_utils.IDE_REGISTRY / skill_profile_detect.VALID_IDES / providers) into one source of truth with a guard test. G6: session model recording for non-Claude hosts (TAUSIK_AGENT_MODEL) so cost/pinning survive under GLM. Also: separate 'bundled framework root' from 'vendored copy' so hooks+MCP resolve from a single hosted location.

## Acceptance Criteria

## Plan

## Rollback

## Journal
