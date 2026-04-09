**English** | [Русский](../ru/mcp.md)

# TAUSIK MCP — Tool Reference

80 tools for the AI agent (73 project + 7 RAG). Use MCP tools instead of CLI bash calls.

## Status and Metrics

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_health` | Health check: version, DB, tables | -- |
| `tausik_status` | Project overview: tasks, session, epics | -- |
| `tausik_metrics` | SENAR metrics: Throughput, FPSR, DER, Dead End Rate, Cost/Task | -- |
| `tausik_search` | Full-text search across tasks, memory, decisions | `query` |

## Tasks

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_task_add` | Create task (optionally in a story) | `slug`, `title` |
| `tausik_task_quick` | Quick creation with auto-slug | `title` |
| `tausik_task_start` | Start work (QG-0: requires goal + AC) | `slug` |
| `tausik_task_done` | Complete (QG-2: `ac_verified=true`) | `slug` |
| `tausik_task_show` | Full task information | `slug` |
| `tausik_task_list` | List tasks with filters | -- |
| `tausik_task_update` | Update fields (goal, AC, scope, notes) | `slug` |
| `tausik_task_plan` | Set plan steps | `slug`, `steps[]` |
| `tausik_task_step` | Mark step as completed | `slug`, `step_num` |
| `tausik_task_log` | Add journal entry | `slug`, `message` |
| `tausik_task_block` | Block task | `slug` |
| `tausik_task_unblock` | Unblock | `slug` |
| `tausik_task_review` | Move to review | `slug` |
| `tausik_task_delete` | Delete task | `slug` |
| `tausik_task_move` | Move to another story | `slug`, `new_story_slug` |
| `tausik_task_next` | Pick next task | -- |
| `tausik_task_claim` | Claim task (multi-agent) | `slug`, `agent_id` |
| `tausik_task_unclaim` | Release task | `slug` |

### `tausik_task_add` Parameters
- `story_slug` -- parent story (optional)
- `goal` -- task goal
- `role` -- role (free text)
- `complexity` -- `simple` / `medium` / `complex`
- `stack` -- technology stack
- `defect_of` -- parent task slug (for defect tracking)

### `tausik_task_update` Parameters
- `title`, `goal`, `notes`, `acceptance_criteria`, `scope`, `stack`, `complexity`, `role`

### `tausik_task_done` Parameters
- `ac_verified` -- **required** for QG-2 (confirms AC verification)
- `no_knowledge` -- confirm no knowledge to capture (suppresses warning)
- `relevant_files[]` -- files modified in the task

## Sessions

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_session_start` | Start session | -- |
| `tausik_session_end` | End session | -- |
| `tausik_session_extend` | Extend session beyond 180 min limit | -- |
| `tausik_session_current` | Current active session | -- |
| `tausik_session_list` | List sessions | -- |
| `tausik_session_handoff` | Save handoff data | `handoff` (object) |
| `tausik_session_last_handoff` | Get handoff from previous session | -- |

## Hierarchy (Epics and Stories)

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_epic_add` | Create epic | `slug`, `title` |
| `tausik_epic_list` | List epics | -- |
| `tausik_epic_done` | Complete epic | `slug` |
| `tausik_epic_delete` | Delete (cascade: stories + tasks) | `slug` |
| `tausik_story_add` | Create story in epic | `epic_slug`, `slug`, `title` |
| `tausik_story_list` | List stories | -- |
| `tausik_story_done` | Complete story | `slug` |
| `tausik_story_delete` | Delete (cascade: tasks) | `slug` |
| `tausik_roadmap` | Tree: epic -> story -> task | -- |

## Knowledge

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_memory_add` | Save to project memory | `type`, `title`, `content` |
| `tausik_memory_search` | Full-text search in memory | `query` |
| `tausik_memory_list` | List entries (filter by type) | -- |
| `tausik_memory_show` | Show entry by ID | `id` |
| `tausik_memory_delete` | Delete entry | `id` |
| `tausik_decide` | Record architectural decision | `decision` |
| `tausik_decisions_list` | List decisions | -- |

Memory types: `pattern`, `gotcha`, `convention`, `context`, `dead_end`

## Graph Memory

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_memory_link` | Create link between nodes | `source_type`, `source_id`, `target_type`, `target_id`, `relation` |
| `tausik_memory_unlink` | Soft-invalidate link | `edge_id` |
| `tausik_memory_related` | Find related nodes (1-3 hops) | `node_type`, `node_id` |
| `tausik_memory_graph` | List links with filters | -- |

Relation types: `supersedes`, `caused_by`, `relates_to`, `contradicts`

## Dead Ends and Explorations

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_dead_end` | Document a failed approach | `approach`, `reason` |
| `tausik_explore_start` | Start investigation (time-boxed) | `title` |
| `tausik_explore_end` | End investigation | -- |
| `tausik_explore_current` | Current investigation | -- |

## Quality Gates

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_gates_status` | Status of all gates (by stack) | -- |
| `tausik_gates_enable` | Enable gate | `name` |
| `tausik_gates_disable` | Disable gate | `name` |

Available gates: `pytest`, `ruff`, `mypy`, `bandit`, `tsc`, `eslint`, `go-vet`, `golangci-lint`, `cargo-check`, `clippy`, `phpstan`, `phpcs`, `javac`, `ktlint`, `filesize`

## Skills

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_skill_list` | List all skills: active, vendored, available | -- |
| `tausik_skill_install` | Install skill from repo (copy + deps) | `name` |
| `tausik_skill_uninstall` | Uninstall skill completely | `name` |
| `tausik_skill_activate` | Activate installed skill | `name` |
| `tausik_skill_deactivate` | Deactivate skill | `name` |
| `tausik_skill_repo_add` | Add TAUSIK-compatible skill repo | `url` |
| `tausik_skill_repo_remove` | Remove skill repo | `name` |
| `tausik_skill_repo_list` | List repos and available skills | -- |

## Audit and Maintenance

| Tool | Description | Required Parameters |
|---|---|---|
| `tausik_audit_check` | Check if audit is needed (SENAR Rule 9.5) | -- |
| `tausik_audit_mark` | Mark audit as completed | -- |
| `tausik_events` | Audit log (events) | -- |
| `tausik_update_claudemd` | Update dynamic section in CLAUDE.md | -- |
| `tausik_fts_optimize` | Optimize FTS5 indexes | -- |
| `tausik_health` | Server health check | -- |
| `tausik_team` | Tasks by agents | -- |

## Codebase RAG (separate MCP server)

| Tool | Description | Required Parameters |
|---|---|---|
| `search_code` | Search project code via RAG index | `query` |
| `search_knowledge` | Search project knowledge base | `query` |
| `reindex` | Reindex the codebase | -- |
| `rag_status` | RAG index status (size, date) | -- |
| `archive_done` | Archive completed tasks | -- |
| `cache_web_result` | Cache web search result for reuse (saves tokens) | `query`, `content` |
| `search_web_cache` | Search cached web results before new requests | `query` |
