# Context economy in 1.11

**English** | [Русский](../ru/context-economy.md)

<!-- doc-map: reader=maintainer; zone=reference -->

TAUSIK now separates a small invariant contract from task-specific context.
New projects use `context_tier: minimal`; existing rules files remain untouched
until their owner regenerates or edits them.

Measured in this repository on 2026-10-01:

| Repeated source | Before | After | Change |
|---|---:|---:|---:|
| Root `AGENTS.md` static instructions | 17,078 B | 4,602 B | -73.1% |
| Claude SessionStart context | 8,670 B | 1,059 B | -87.8% |
| Generated rules (`standard` to measured `minimal`) | 15,533 B | about 6,000 B | about -61% |

The task package is loaded once when work starts rather than repeated as a
global rule. The live 1.11 context task package is 6,007 B against an 8,192 B
default budget. It contains goal, acceptance criteria, paths, active decisions,
unresolved risk and verification commands. Required fields are never shortened:
an oversized contract is returned whole with explicit overflow. Optional memory
is admitted line by line and names the omitted range.

The task skill requests the package in the successful start result, removing a
dependent model turn:

```bash
.tausik/tausik task start <slug> --package
```

MCP uses `tausik_task_start(slug=..., package=true)`. The previous workflow was
`task_start` followed by `task_show(package)`: two model responses and two tool
calls on a successful start. The compound route is one response and one call.
QG-0 still runs before activation. If the read-only projection fails after the
activation commits, the envelope says `started=true, ok=false` and supplies the
targeted recovery command; it never reports the partial result as success.

For targeted recovery or a later refresh, use MCP `tausik_task_show` with
`mode=package`, or:

```bash
.tausik/tausik task show <slug> --package --max-bytes 8192
```

The package fingerprint changes when task intent, paths, risk, plan or active
decisions change. Superseded decisions are excluded. Tests cover omitted
memory, required-field overflow and superseded decisions on the shared path
used by Codex, Claude and GLM hosts.

Codex native `turn_context` records observed in this environment expose no
tool-schema field or explicit `tools_deferred` signal. Tool-schema deferral is
therefore **unknown**. TAUSIK does not claim savings from schema deferral.

The project does control the surface its own MCP server advertises. On
2026-10-02, a fresh stdio process was measured before and after enabling the
existing `mcp.compact_tool_list` project flag. Both measurements used the same
147-tool `tools/list` response and minified UTF-8 JSON; source-file size and a
stale already-running MCP process were excluded.

| Eager project-controlled source | Before | After | Change |
|---|---:|---:|---:|
| `AGENTS.md` | 7,518 B | 7,518 B | 0 B |
| Canonical skill catalog (15 names + descriptions) | 1,249 B | 1,249 B | 0 B |
| MCP names | 3,974 B | 3,974 B | 0 B |
| MCP descriptions | 17,722 B | 11,897 B | -5,825 B |
| MCP schemas | 32,134 B | 17,145 B | -14,989 B |
| MCP JSON structure | 736 B | 736 B | 0 B |
| **Eager total** | **63,333 B** | **42,519 B** | **-32.9%** |

The rows are an exact non-overlapping partition: MCP field fragments plus JSON
structure add to the serialized list, while `AGENTS.md` and the skill catalog
are counted once. The 89,315 B of skill bodies are reachable on demand and are
reported separately, so they are not added to the eager total. Non-core tool
names and short descriptions remain visible; their complete descriptions and
schemas are retrieved by exact name through
`tausik_tool_schema(name=...)`. Core session, task, verification, memory,
search, doctor and recovery operations keep their complete eager definitions.
This deterministic server-side reduction does not change the earlier statement
about unknown native Codex schema accounting.

The one-call count is deterministic on the shared Codex, Claude and GLM skill.
Live GLM quota and retry savings remain unmeasured until the release acceptance
run; TAUSIK does not translate the saved call into a token or subscription
quota claim. Retry cases and measurement boundaries are recorded in the
[1.11 compound workflow note](../ru/research/compound-workflow-111.md).
