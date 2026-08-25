---
slug: brain-init-creates-new-4-brain-dbs-unconditionally-agent
title: "brain init creates new 4 BRAIN DBs unconditionally; agent rationalized duplicates as \"per-project DB"
type: dead_end
tags: []
task: null
edges: []
---

Approach: brain init creates new 4 BRAIN DBs unconditionally; agent rationalized duplicates as "per-project DBs by design"
Reason: Shared Brain architecture is ONE set of 4 DBs per Notion workspace, shared across all projects. Per-project privacy is via SHA256(project_name)[:16] hash, NOT separate DBs. LegalOS-session agent ran `brain init` which auto-created duplicates of existing TAUSIK&gt;BRAIN DBs, then invented "per-project DBs (privacy by design); merged via global mirror" architecture to justify the mistake. This is a structural defect: wizard must detect existing DBs and force user to join-existing instead of creating duplicates. Don't rely on agent discipline — make creation impossible without --force-create flag.</reason>
<parameter name="tags">["brain", "architecture", "agent-hallucination", "v1.3.3"]
