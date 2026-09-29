**English** | [Русский](../ru/cli-knowledge.md)

# CLI: knowledge and search

<!-- doc-map: reader=user; zone=core-surface -->

Memory, dead ends, exploration, search, log. Part of the command reference. Start, and the working set, in [cli.md](cli.md).
## Knowledge

```bash
knowledge promote --memory ID | --decision ID [--yes]   # Copy an existing record to the shared store: shows the whole text first, writes only with --yes, keeps origin project/slug, refuses a second copy
decide <text> [--task SLUG] [--rationale TEXT] [--global]   # --global: the shared store ~/.tausik-knowledge, no project row
    [--rejected "option :: why" ...] [--supersedes N --because TEXT]
    # --rejected is repeatable and optional; --supersedes needs a reason and an existing N
decisions [--limit N] [--status all|active|superseded] [--task SLUG] [--rejected QUERY]
                                # superseded decisions are never deleted: they leave `active`
                                # and the memory block, and show who replaced them

memory add <type> <title> <content> [--tags T1 T2 ...] [--task SLUG] [--global]
           [--provenance observed|inferred|told]   # default inferred; observed must name a test,
           # a verify run (verify #N) or a task with a journal, otherwise it is downgraded and says so
memory list [--type TYPE] [--limit N]
memory search <query>           # FTS5 full-text search
memory show <id>
memory delete <id>
memory edit <id> [--title T] [--content C]  # rewrite a record, keeping its id, slug and created_at

# Graph memory (Graphiti-inspired)
memory link <source_type> <source_id> <target_type> <target_id> <relation>
            [--confidence 0.0-1.0] [--created-by AGENT]
memory unlink <edge_id> [--replacement EDGE_ID]   # Soft-invalidate (never deletes)
memory related <node_type> <node_id> [--hops N] [--include-invalid]
memory graph [--type {memory,decision}] [--id N]
             [--relation {supersedes,caused_by,relates_to,contradicts}]
             [--include-invalid] [--limit N] [--format {table,mermaid}]
             # --format mermaid: emit the graph in Mermaid notation (for doc rendering); default table

# Aggregators
memory block [--max-decisions N] [--max-conventions N] [--max-deadends N] [--max-lines N]
memory compact [--last N]

# Hygiene (v1.5)
memory archive --before <duration> [--confirm]    # Soft-archive memory older than duration
                                                   # (90d / 12w / 2m / 1y). Dry-run by default;
                                                   # --confirm stamps archived_at, idempotent.
memory dedupe [--threshold 0.85] [--limit 200]     # List near-duplicate pairs above similarity
                                                   # threshold (difflib.SequenceMatcher.ratio()
                                                   # over title || content). Read-only.
```

**Memory types:** pattern, gotcha, convention, context, dead_end
**Graph node types:** memory, decision
**Relation types:** supersedes, caused_by, relates_to, contradicts

## Dead End Documentation (SENAR Rule 9.4)

```bash
dead-end <approach> <reason> [--task SLUG] [--tags T1 T2 ...]
    # Since 1.10 a dead end names its task: without --task it binds to the single active
    # task, and with none or several active it is refused. A task that saw a failure
    # (a red verify, a block, a second attempt) closes only with a dead end linked to it
    # or a journal line `NO-DEAD-END: <why there is none>` (10+ characters).
# Documents a failed approach with reason. Saved as memory type dead_end.
```

## Exploration (SENAR Section 5.1)

```bash
explore start <title> [--time-limit MINUTES]    # Start investigation (default: 30 min)
explore end [--summary TEXT] [--create-task]    # End (--create-task creates a task from findings)
explore current                                 # Show active exploration with elapsed time
```

## Search and Navigation

```bash
roadmap [--include-done]        # Full tree epic -> story -> task
search <query> [--scope {all,tasks,memory,decisions}]
```

## Events (Audit Log)

```bash
events [--entity {task,epic,story}] [--id SLUG] [--limit N]
       [--full] [--top-n N] [--max-lines N]
```

Above 25 rows the output rolls up by entity-type and action (a compact,
deterministic aggregate) instead of dumping every event; `--top-n` / `--max-lines`
cap the group lines and a footer names how many are hidden. `--full` prints the
per-event dump unchanged. `task list` takes the same three flags (rolls up by
status and role).

## Snippets / clone detection (v15-snippet)

```bash
snippet detect [--path X] [--threshold N]  # AST clone detection: normalizes
                                           #   identifiers/literals to placeholders,
                                           #   hashes def/class subtrees, clusters
                                           #   >=2 matches and writes them to the
                                           #   snippets table (taxonomy_kind='clone').
                                           #   --threshold = minimum candidate line
                                           #   count (default 10).
                                           #   Idempotent (deduped by hash).
```

## Redacting from memory (v1.9)

The task journal is append-only, memory has no `update`, decisions have only
`list`. That is deliberate: a record that can be quietly rewritten stops being
evidence. But irrevocability must have a paired mechanism, or the first line
recorded in error becomes permanent.

`redact` is that mechanism. It is an **overwrite that leaves a trace**, not a
deletion.

```bash
# Dry run — THE DEFAULT. Writes nothing, shows what it would touch.
tausik redact --pattern "internal.example.com" --label internal-host \
              --reason "a private host address does not travel to a public repo"

# Apply. IRREVERSIBLE.
tausik redact --pattern "internal.example.com" --label internal-host \
              --reason "..." --apply

# By regular expression instead of a literal
tausik redact --regex --pattern "alpha|beta|gamma" --label third-party-project --reason "..."

# What has been redacted in this project
tausik redact list --limit 50
```

**A bad regular expression is refused in words, not in a traceback.** `--regex`
with an unparseable pattern gives a named refusal with exit code 1: the command
names the pattern AS TYPED and quotes `re`'s explanation together with the error
position. The pattern is printed without repr quotes on purpose — `re` reports
the fault BY POSITION, and repr doubles backslashes and would shift every index.
The refusal happens BEFORE any read or write, and it is distinguishable from the
neighbouring "zero matches" outcome: an unparseable pattern and an empty result
are different answers with different remedies.

**What happens to the text.** A match is replaced by the visible marker
`[redacted: <label>]`. The reader must see that something stood here: a silently
shortened sentence is indistinguishable from one that always read that way.

**What happens to the trace.** Every touched column gets a row in the
`redactions` table: the entity, the field, the CLASS of what was redacted, the
reason, the number of replacements, the time. The trace is neither deleted nor
edited — it is the only reason an irrevocable journal can still be trusted once
rewriting became possible.

**`--label` names the class, not the value.** A trace quoting the secret would
put the leak back into the database, in a column nobody would think to scan.

**Scope.** Prose columns only, declared in one place —
`scripts/redact_scope.py`. Structural columns (`slug`, `status`, timestamps,
foreign keys) are excluded: those are addresses, not text, and rewriting an
address breaks the rows that reference it while removing nothing a human wrote.

**There is no restore.** The original text is stored nowhere — not in the trace,
not in a shadow copy. The only way back is a backup of `.tausik/tausik.db` taken
BEFOREHAND; the dry run says so before anything is written.

**After applying, run `tausik state export`** — the projection is generated from
the database, and until it is rebuilt the tree still shows the old text.

**Zero matches is its own outcome, not a success.** The command says "no match"
in its own words: a caller convinced there is a leak must learn that the pattern
was wrong, rather than receive a clean exit indistinguishable from real work.
