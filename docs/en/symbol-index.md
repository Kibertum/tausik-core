# `tausik symbol` — the definition, not the address

The usual route to somebody else's function costs two calls: `grep` to find it,
then a file read to look at it. `tausik symbol <name>` answers in one: path and
line, the body of the definition, and who calls it.

RU mirror: [`../ru/symbol-index.md`](../ru/symbol-index.md).

## Where this comes from

From [Graft](https://github.com/trailhq/Graft), a context layer for coding
agents. What transfers is its DETERMINISTIC half: the symbol graph is built by
parsing sources with no model involved, and a query returns the source INSIDE the
answer so the file need not be opened afterwards. Graft is TypeScript on
tree-sitter; this is Python on `ast`, because that is what the project can carry
without a dependency.

The explanation layer, which in Graft is written by a model, is deliberately NOT
copied: it needs a key, a network and money, and the measurable half of the
saving is in the deterministic part.

## Why — measured, not felt

Session #233, eight transcripts, 4,826,406 characters of tool result payload:

| What | Share |
|---|---|
| Code navigation by TOOL NAME (Read, Grep, Glob, ToolSearch) | 9.6% |
| `grep`/`sed`/`find`/`ls` inside Bash — 1,192 calls at 1,501 chars | 37.1% |
| **Code exploration, really** | **about 47%** |

The first count said "not worth it": a ceiling of about 2.7% of context growth.
Counting by what the commands actually DO reversed the conclusion — half the
reconnaissance here wears the name `Bash`. That is decision #335 in a new place:
check the fact, not the presence of a name.

## What the measurement says after building it

25 random functions of 8 lines or more:

| Way | Calls | Characters |
|---|---|---|
| `grep` + `sed` | 2 | 30,517 |
| `symbol`, no callers | 1 | 29,442 (−3.5%) |
| `symbol`, with callers | 1 | 34,686 (+13.7%) |

**The saving is in CALLS, not in the size of an answer.** That is exactly the
economy decision #338 defines: every call re-sends the whole conversation, and
this project's baseline puts a call at 266,645 context tokens. The extra 13.7%
buys the caller list — a question that would otherwise cost a third call.

Graft's own numbers (42% tokens, 46% tool calls) do NOT transfer: they were
measured on other repositories. The agreement on calls is a coincidence, not a
borrowing.

## Using it

```bash
.tausik/tausik symbol tags_unmoved              # definition + callers
.tausik/tausik symbol Holder.method             # a method of a class
.tausik/tausik symbol answer --lines 20         # a shorter body
.tausik/tausik symbol build_index --no-callers  # skip the tree walk, faster
```

## Limits, stated rather than discovered

* **The index is DERIVED from the tree and never edited.** It is rebuilt on every
  query (13,199 symbols in 1.2 s), so it cannot go stale. A hand-maintained
  symbol registry would rot the way every other hand-maintained registry here has.
* **Callers are found BY NAME.** Two functions sharing a name yield one list;
  resolving that needs type inference, which `ast` does not do. A list that says
  so beats a list that quietly picks one.
* **`scripts`, `bootstrap`, `tests`, `harness` are indexed.** A symbol outside
  them is out of the index by design, and the refusal says so rather than going
  quiet.
* **Sources are PARSED, never imported.** An import would execute module-level
  code from every file in the tree during indexing.
* **The answer is bounded and the cut is named.** A silent truncation teaches the
  reader to open the file anyway, which is paying twice.
