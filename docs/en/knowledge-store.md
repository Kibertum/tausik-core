**English** | [Русский](../ru/knowledge-store.md)

# The shared knowledge store — what it is, and how it differs from project memory

New in 1.8. A local file, `~/.tausik-knowledge/knowledge.db`, one per person
rather than one per project.

This page answers two questions: **how it works** and **how it differs from the
project database**. There are two stores and no third: the Notion transport that
used to mirror this one outward left the framework in 1.9 (decision #358). (The
routing table bootstrap writes into a project names a third DESTINATION — the
host's own auto-memory — but that one is the host's, not a TAUSIK store.)

---

## Why it exists

Project memory (`.tausik/tausik.db`) knows everything about its own repository
and nothing about the one next to it. With one project that is invisible. With
three it becomes expensive: the dead end you hit on Monday, and wrote down, is
one you will hit again in the next project — because the note stayed in another
folder and search does not go there.

The shared store is where things go that are true **not in this project, but in
general**.

---

## How it differs from project memory

|  | Project database | Shared store |
|---|---|---|
| **Where** | `.tausik/tausik.db` inside the repository | `~/.tausik-knowledge/knowledge.db` in your home |
| **How many** | one per project | one per person |
| **What it holds** | tasks, sessions, verifications, decisions, memory, metrics — the whole lifecycle | knowledge ONLY: `pattern`, `gotcha`, `convention`, `context`, `dead_end` |
| **What it outlives** | lives and dies with the repository | outlives the deletion of any project |
| **Who reads it** | this project | ANY project on this machine |
| **Does it travel in git** | no — `.tausik/` is gitignored; the `tausik/` projection is what travels | no, and it must not |
| **Is the content redacted** | no | **no** — written verbatim, no scrubber |
| **Is it visible outside** | no | no; it does not leave the machine |
| **Backup** | database copies alongside it | `tausik knowledge export`, and that stays here too |

The "is the content redacted" row is the load-bearing one, and it comes back
below.

---

## The rule: what goes where

A formulation you can check rather than feel:

> **A fact about THIS project goes in project memory. A statement true in ANY
> project goes in the shared store.**

The test, on the spot: imagine reading the entry six months from now, in a
**different** repository, for a different client. Meaningless there? Project
memory. Useful? Shared.

**Error of the first kind — putting project-specific things in the shared store.**

```
❌ --global "auth_middleware.py line 42 logs an e-mail address"
```

Another project has neither that file nor that line. The entry will surface in
search and get in the way. Worse: it names the internals of one repository in a
store that every project on the machine reads.

```
✅ (project)  "auth_middleware.py line 42 logs an e-mail address"
✅ --global   "Logging a whole request object is a routine way to leak PII —
               audit serializers, not just explicit prints"
```

**Error of the second kind — leaving general knowledge in project memory.**

```
❌ (project) "FTS5 MATCH breaks on a hyphen in the query — escape it"
```

That is a property of SQLite, not of your repository. Next month you will pay the
same hour for it again somewhere else.

---

## Commands

**Put knowledge in the shared store:**

```bash
tausik memory add pattern "Title" "Body" --global
tausik memory add gotcha "Title" "Body" --global --tags sqlite fts5
```

`--global` puts the entry in the shared store **or fails saying so**. It cannot
quietly fall back to project memory — you would believe the knowledge was shared
while it sat in a single repository.

**Find it:** search reads **both** stores and marks which one a row came from.

```bash
tausik search "fts5 hyphen"
```

The knowledge block injected at session start reads both as well.

**Backup and restore:**

```bash
tausik knowledge export --to ~/backup/knowledge     # one readable file per record
tausik knowledge restore --from ~/backup/knowledge  # records matched by uuid
```

The export is not a dump but a file per record: readable by eye, storable in a
private dotfiles repository, and comprehensible a year later. `restore` matches
on `uuid`, so running it twice does not duplicate anything.

**A backup that leaves the machine goes through the publication boundary.**
The store is kept unredacted — a memory can name a client outright — and the
only argument for that is "it never leaves the machine". A plain export refuses
remote destinations (`s3://`, `https://`, UNC) and stays faithful for restore.
For a copy that will travel, add `--redacted`:

```bash
tausik knowledge export --to ~/travel/knowledge --redacted
```

Every text field then passes `publication_boundary.redact`: absolute paths,
e-mails, private URLs (`publication.private_url_patterns` in the config) and
project names (this project's directory name plus `publication.project_names`)
become typed placeholders such as `[REDACTED:email]`, and the manifest records
`redacted: true` with a count per detector. Restoring a redacted backup over a
live store changes nothing — `restore` never overwrites an existing uuid — and
restoring it into an empty store carries the placeholders, never the originals.
The boundary is the one place this question is answered: a test walks the tree
and fails on any module that reads the store and writes files without it.

**One-off import from the retired Notion mirror:**

```bash
tausik knowledge import-brain
```

Copies the local mirror file the Notion transport left behind
(`~/.tausik-brain/brain.db`) into the shared store. No network required, and
nothing to configure: the transport itself is gone since 1.9 (decision #358).

**Where is it right now:** `tausik doctor` prints the resolved store path, and
names the reason when a location is refused.

---

## What it deliberately does NOT do

This is not a list of gaps. Each item is a decision.

**It does not redact content on write.** Text enters the shared store as
written: no scrubber, no path stripping, no name substitution. The entire
justification is that **the store never leaves this machine** — and the one
command that makes it leave, `knowledge export --redacted`, is where redaction
happens (see the publication boundary above).

**It does not leave the machine.** Hence the `TAUSIK_HOME` validation added in
1.8: a network path (UNC or a mapped volume) and a cloud-sync directory
(OneDrive, Dropbox, Google Drive, iCloud, Yandex.Disk, `~/Library/CloudStorage/`)
are **refused**, as is a store git is already tracking. "It never leaves" is a
property of a DIRECTORY, not of code, and that variable names the directory.
`~/OneDrive` sits inside your home, so "it is in my home" stayed true while the
conclusion drawn from it did not. See [whats-new-1.8.md](whats-new-1.8.md),
change 6.

**It does not sync between machines.** With no second copy there is no merge.
Moving it is manual, via `export` and `restore`.

**It does not record which client a row came from.** `origin_project` used to
hold the ABSOLUTE root of the originating project: on a machine serving several
clients, one client's directory name was readable from another client's project.
It now holds a `basename@fingerprint` label. Existing rows are rewritten on the
next open.

**It is not a transport.** Two stores, two answers to "where does this go",
and both are chosen by you:

| Command | Destination | Leaves the machine |
|---|---|---|
| `tausik memory add ...` | project database | no |
| `tausik memory add ... --global` | shared store on this machine | no |
| `tausik knowledge export --to <dir> --redacted` | a local directory, redacted | only if you carry it |

Nothing routes itself and nothing publishes: the classifier that used to decide
went in 1.8 (decision #221), the Notion transport in 1.9 (decision #358).

---

## Compatibility

A TAUSIK older than the store's schema **refuses to run** and says which version
is required, rather than guessing at the format and corrupting the file. The
other direction is safe: a newer TAUSIK migrates an older store on open.

The move from `~/.tausik/` (the pre-1.8 address) happens on its own: the store is
**copied** from the old location on first use, and only when the new location is
empty. Copied rather than moved — deleting things inside someone's home directory
is theirs to decide. One exception: with `TAUSIK_HOME` set, adoption does not run
at all and the move is yours.

---

## See also

- [whats-new-1.8.md](whats-new-1.8.md) — what changed in 1.8, including the move
  and the `TAUSIK_HOME` validation.
- [memory-merge-guidelines.md](memory-merge-guidelines.md) — when to merge an
  entry and when to write a new one.
- [architecture.md](architecture.md) — where the `knowledge_*` modules live.
