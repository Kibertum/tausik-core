**English** | [Русский](../ru/whats-new-1.10.md)

# What changed in 1.10

<!-- doc-map: reader=user; zone=release-notes -->

A page for someone upgrading. What it is for first, then what breaks.

## What 1.10 is, in three points

**🤖 Autonomy stopped being a request and became a mechanism.** 1.9 asked the
agent to keep going, and the measurement said what an ask is worth: a rule that
is only asked for gets switched off the same week. 1.10 has `/run`, a driver
that closes tasks one after another inside a single turn; the call budget
became a CEILING in an unattended run and stayed advice everywhere else; and a
run watches its own capacity and stops BETWEEN tasks rather than halfway
through one. The promise of autonomy itself became a number — closures per
owner message — because a promise with no number has nothing to check it.

**📐 A claim is now either measured or declared absent.** A quantity that
cannot be obtained is not passed off as zero (that rule came in 1.9 and
stands); what is new in 1.10 is that COST is a number too. The state
projection's cost was measured: 68.6% of tracked paths and 47.1% of bytes, with
a verdict per kind and the reason none of them leaves. The cost of an answer
was measured: the journal has a budget — and only its RETELLING half does,
because evidence of closure is not capped. And there is now a register of
deliberate gaps: what is NOT guaranteed, with a reason on every line, because a
gap with no reason reads as an unfinished job.

**🔍 The framework stopped believing its own paperwork.** A forged receipt no
longer passes verification. A whole-project gate PASS no longer certifies files
it did not look at. The duplication ratchet measures duplication instead of
similarity. The register of rotted citations is empty: 108 and 39 became zeros.
And semantic search is the one feature of this release that shipped SWITCHED
OFF: the published evidence says there is no effect below a thousand records,
so the gate is closed and the activation rate on our own machine is zero. That
is a result, not a gap.

---

## BREAKING CHANGES

Five. Each with what to do.

### 1. The user tier moved to `~/.config/tausik/config.json`

The old address, `~/.tausik/config.json`, is read **only when it is the only
one**. The reason is not cosmetic: a directory named `.tausik` in the home
folder makes home look like a project to the upward search, so a command run
anywhere would silently attach to the configuration tier instead of a project.

**What to do:** move the file. `tausik doctor` says when both exist.

### 2. `task start --force` is withdrawn

Session time and call capacity became SIGNALS rather than gates. There is no flag to bypass a gate, because there is no gate.

**What to do:** drop `--force` from scripts. The long-session warning stays and
is still worth reading.

### 3. The RAG server's entry point is `rag_server.py`

The file was called `server.py` in two different packages and two map entries
pointed at one, which is why mypy was not checking one of the servers.

**What to do:** if the MCP server is registered by hand, fix the path in
`.mcp.json`. The stock `bootstrap.py` does it for you.

### 4. A TAUSIK session is a host session

Hooks open and close it, not a command. The checkpoint counter is derived from
the journal, and the audit cadence counts CLOSURES rather than sessions.

**What to do:** nothing, if you use the stock hooks. If you called
`session start` from your own scripts, the call is no longer needed.

### 5. `TODO.md` is retired

The document called itself the map of the project's direction and had drifted
two releases behind while a GENERATED `ROADMAP.md` sat beside it. Its 2.0
content is preserved in a decision and in the active epics.

**What to do:** read `ROADMAP.md`. If you linked to `TODO.md`, that link is
dead — which is better than a link to something stale.

---

## What else changes on upgrade

### Database schema: 62 → 67

Five migrations, all forward, none losing a row:

| Version | What arrived |
|---|---|
| v63 | host session: a TAUSIK session is bound to the host's |
| v64 | `SPEC-UC`, the twelfth specification type (RENAR 1.1 §8.3) |
| v65 | a memory row states where its claim came from — observed or inferred |
| v66 | a decision records what it rejected and what later superseded it |
| v67 | fields the task projection added |

The upgrade runs on first launch. A 1.9 defect — a crash on v53 that left the
version at 44 — is fixed; if you are stuck on it, the upgrade will go through.

### New commands

| Command | What for |
|---|---|
| `tausik hygiene unarchive` | clear `archived_at` by slug or by recency — the one way back that did not exist for two releases |
| `tausik memory edit` | rewrite a record with a command instead of going around through the projection |
| `tausik task obsolete` | close a task that time resolved, without passing it off as delivered |
| `tausik metrics answers` | the shape of the agent's answers, measured |
| `tausik db telemetry` | trim accumulating sidecars to their declared lifetime |
| `tausik publish notes` | a release body that refuses itself without both notes pages |
| `/run` | work the release composition task by task without handing control back |

### Search: inflection, quoting, and silence

Search finds a word in any case and number. Four FTS paths stopped crashing on
a query written the way names are written in this project: `memory search` with
two words failed roughly half the time. Code search no longer returns files
that do not exist.

### Shipped, and off by default

Semantic re-rank over FTS5 is **off**, and worth switching on only past a
thousand records: below that the published evidence shows no effect, while the
provider round-trip is paid every time. The provider endpoint must be loopback —
the service is handed whole rows verbatim, and a hosted endpoint would take
them off the machine.

Compact MCP tool schemas (`mcp.compact_tool_list`) are **off**.

### Hygiene you will notice

Empty directories git cannot see became a finding. Accumulating telemetry has a
lifetime, and it follows the READER: a file whose reader needs all of it is not
trimmed by age at all. Database backups are pruned by version number rather
than by modification time.

### Answers got shorter, and that is measured

An agent's answer now has a budget it sees on the next request, and
`tausik metrics answers` puts a number on the shape of answers. The rule is
about RETELLING: evidence of closure is not capped.

---

## What is NOT in this release

Better said than left out:

* **tausik.tech is not rebuilt.** It serves documentation four releases old.
  The task is blocked by two of its own criteria: the build takes the core BY
  TAG, and there is no tag before the release, and deploying outward is the
  owner's act.
* **There is still no measured token saving.** The 1.9 measurement stands as the
  last word: on that pair there was no saving. 1.10 did not re-measure it, and
  there is nothing to claim the opposite with.
* **The host's answer to `session.list_roots()` is unverified.** The probe needs
  a server registered in the config and a host restart; it is recorded as
  unverified, with a review date.

---

## See also

- [known-limitations.md](known-limitations.md) — the full register of what is NOT guaranteed
- [state-projection-cost.md](state-projection-cost.md) — what the projection costs and why every kind stays
- [semantic-rerank.md](semantic-rerank.md) — the gates on the semantic layer and the measurement on our own traffic
- [task-archive-spec.md](task-archive-spec.md) — archival and the one command back
- [publishing.md](publishing.md) — the two lines of the repository and why a published tag does not move
