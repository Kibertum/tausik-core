# What changed in 1.8

For anyone upgrading. Six breaking changes with migrations first, then what is
new.

Full list of changes: [CHANGELOG.md](../../CHANGELOG.md).

---

## BREAKING CHANGES

### 1. The classifier no longer decides what gets published: `decide` NEVER publishes on its own

**Before.** `tausik decide` ran the text through a classifier; if it judged the
decision "general", the page went to Notion automatically.

**Now.** The author decides visibility, always:

| Command | Where it goes |
|---|---|
| `tausik decide "..."` | this project only |
| `tausik decide "..." --global` | the local shared knowledge store |
| `tausik brain move --to-brain <id>` | outward — and only this way |

**Why this is breaking rather than hygiene.** The defect was not that the
heuristic sometimes chose wrong; it was that the heuristic was making the
publication decision at all. Judging by textual markers, it had already sent SIX
internal decisions outward — among them the decision to cancel the 2.0 plan and
the decision on the release date. Every session added pages.

**Migration.** Nothing to do, but check: if your workflow relied on decisions
appearing in Notion by themselves, they must now be published explicitly.
Already-published pages are untouched — 1.8 deletes nothing outside.

**Does this affect you?** You have seen Notion pages you did not create by hand.

---

### 2. The shared knowledge store moved from `~/.tausik/` to `~/.tausik-knowledge/`

**Before.** `~/.tausik/knowledge.db`.
**Now.** `~/.tausik-knowledge/knowledge.db`; overridable with `$TAUSIK_HOME`.

**Why.** `~/.tausik` was a defect, proven by measurement. Project discovery
(`find_tausik_dir`) walks UP the directory tree looking for exactly the name
`.tausik`. A shared store in the home directory therefore captured project
discovery for everything beneath it: from any directory without its own
`.tausik`, TAUSIK treated the home directory as the project. The precedent was
right there — brain has always lived in `~/.tausik-brain`, outside the search.

**Migration: nothing to do.** The store is adopted from the old address on first
use — `adopt_legacy_store_if_present` COPIES it to the new location. Copies
rather than moves: the old directory may hold other things, and deleting inside
someone's home directory is theirs to decide, not ours. Adoption only ever runs
when the new location is absent, so it cannot overwrite a store already there.

**One exception, and it is yours.** If `TAUSIK_HOME` is set, adoption does not
run at all: an explicitly named home is a named address, and reaching into it
for data the caller did not point at is not the framework's call. There, the
move is on you:

```bash
mkdir -p "$TAUSIK_HOME"
mv ~/.tausik/knowledge.db "$TAUSIK_HOME/knowledge.db"
```

**⚠️ Do not recreate `~/.tausik/`** — see the interaction under change 3. The
old directory left behind after adoption can be deleted by hand; while it
exists it keeps masquerading as a project for everything under your home.

**Check:** `ls ~/.tausik-knowledge/knowledge.db` — the file is there.

---

### 3. Config trust tiers: the project tier may only TIGHTEN

**Before.** A gate disabled in `.tausik/config.json` stayed disabled.
**Now.** The project tier may only tighten supervision, never loosen it. Such a
disable is IGNORED, the gate runs enabled again, and `tausik doctor` names the
rejected key.

**Migration.** Move the loosening to a trusted tier:

```bash
# option A — user tier
$EDITOR ~/.tausik/config.json
# option B — managed tier (for an organisation)
export TAUSIK_MANAGED_CONFIG=/etc/tausik/config.json
```

**⚠️ INTERACTION WITH CHANGE 2, called out here because otherwise it gets
discovered the hard way.** Option A creates `~/.tausik/` — precisely the
directory change 2 exists to remove. Project discovery will again treat the home
directory as a project for any run started from a directory with no `.tausik` of
its own above it.

If that affects you, use the environment override instead of a file in the home
directory — it creates no directory:

```bash
export TAUSIK_USER_CONFIG=~/.config/tausik/config.json
```

Or use option B, which creates nothing under `~` at all.

**Does this affect you?** `tausik doctor` — look for the rejected-config-key
line.

---

### 4. Verify receipt schema: v1/v2 → v3

**Before.** A receipt carried `files_hash` — an opaque digest you can compare
but cannot read.
**Now.** `tausik-receipt/v3` adds `files` (the path list), `gate_signature` (the
gate-set digest) and a signed `expires_at`.

**What happens to old receipts.** v1 and v2 receipts remain cryptographically
VALID, and the previous close path (searching for a fresh run) accepts them as
before. But such a receipt cannot be PRESENTED against the new handle: it names
neither what it covered nor which gates ran. The refusal lists the missing
fields by name.

A v1 receipt's scope still reads as UNVERIFIED, never as complete.

**Migration.** External tools that parse receipts must handle the three new
fields. Nothing to do otherwise: the next `tausik verify` emits v3.

Details: [receipts.md](receipts.md).

---

### 5. A verify run with no declared scope no longer certifies anything

**Before.** `tausik verify --task X`, run before the task declared its
`relevant_files`, recorded a green against an empty file set — and that green
stayed usable for the whole cache TTL.

**Now.** An undeclared scope is treated as "unknown", not as "verified empty".
An empty-scope run is still recorded, so it stays observable, but it cannot be
reused to close a task.

**Why this is breaking rather than a tightening.** Two properties combined into
a hole. `gate_runner` SKIPS the scoped gates when no files are declared, so the
run proved nothing about any file; and `compute_files_hash([])` returns a stable
empty marker that no edit ever moves, so the green never went stale. The
sequence verify → edit → `task done` therefore passed QG-2 on a green taken
before the edit. The refusal is enforced ahead of the `task_done.auto_verify`
opt-out, not after it, because `.tausik/config.json` travels with the repository
and is not a safe place to keep a bypass.

**Migration.** A task must declare `relevant_files` to close on a verify green:

```bash
tausik verify --task <slug> --relevant-files <paths...>
```

Closing on an undeclared scope now blocks, and the message names that as the
reason rather than asking for another `tausik verify` that could never succeed.
A full-suite `tausik verify` without `--task` is unaffected — it was never
cached.

**Does this affect you?** You run `tausik verify --task` without
`--relevant-files`, or you rely on `task_done.auto_verify`.

---

### 6. `TAUSIK_HOME` is validated, and some locations are now refused

**Before.** `TAUSIK_HOME` was taken as given — `abspath(expanduser(...))` and
nothing else. Any directory could hold the shared knowledge store.

**Now.** The location is checked before the store opens. A network path (UNC, or
a mapped/mounted network volume) and a cloud-sync directory (OneDrive, including
`OneDrive - Company`; Dropbox; Google Drive; iCloud; Yandex.Disk; the macOS
`~/Library/CloudStorage/` tree) are REFUSED. A store that git is ALREADY
TRACKING is refused. A store merely sitting inside a git work tree is NOT
refused — it gets a `.gitignore` of its own instead, because refusing there
would reject the default location for everyone who keeps their home directory in
a dotfiles repository.

**Why this is breaking rather than hygiene.** It refuses a setup that worked
yesterday, and clearing the refusal takes an action only you can take. The store
is written WITHOUT redaction, and the whole justification on record is that it
never leaves this machine. That is not a property of the code — it is a property
of a directory, and this variable names it. `~/OneDrive` is inside your home
directory, so "it is in my home" stayed true while the conclusion drawn from it
quietly stopped being.

**Migration.** Point `TAUSIK_HOME` at a local directory outside any synced tree,
and carry the store across:

```bash
tausik doctor                          # shows where it resolves today
tausik knowledge export <dir>          # from the OLD location, first
TAUSIK_HOME=<new-local-dir> tausik knowledge restore <dir>
```

If the refusal names git TRACKING, the store is already in a commit: untrack it
with git's cached-removal option and move `TAUSIK_HOME` outside the repository.
An ignore rule does not remove what is already indexed.

**Does this affect you?** You set `TAUSIK_HOME` to a path inside OneDrive,
Dropbox, Google Drive, iCloud or a similar client; to a network share or a
mapped drive; or `knowledge.db` is committed to a repository. If `TAUSIK_HOME`
is unset, the default `~/.tausik-knowledge` is unaffected — unless your home
directory itself is inside a synced tree.

---

## What is new

- **Verify run handles.** `tausik verify --task <slug>` prints
  `<run_id>.<nonce>`; `task done --verify-handle` presents it instead of the
  server searching for a fresh row. Refusals now say what is actually wrong
  ("the files this receipt covers have changed") rather than "cache miss".
  Single-use, one-hour lifetime, validated against the live files and the live
  gate config. SEP-2567 "explicit state handles". The previous behaviour is
  preserved: without `--verify-handle` everything works as before.
- **"Session" split into two things** — work continuity and agent context
  hygiene. An absent session no longer means unlimited capacity: the 200-call
  gate stopped silently waving work through. A handoff no longer requires an
  open session. See [sessions.md](sessions.md).
- **Notion is optional in fact, not just by flag** — see change 1.

## See also

- [upgrade.md](upgrade.md) — the general upgrade procedure.
- [config-trust-tiers.md](config-trust-tiers.md) — the tiers in full.
- [receipts.md](receipts.md) — receipts and handles.
- [sessions.md](sessions.md) — the two halves of a session.
