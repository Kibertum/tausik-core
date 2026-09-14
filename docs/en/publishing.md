# Two lines: where development happens, and what a consumer sees

Decision #267 (29.08): **GitLab is the development line, GitHub is the release
mirror.** It replaced the 25.08 wording ("GitHub becomes the primary place of
development"), which went unexecuted for five sessions straight — branches lived
in GitLab throughout. The decision was brought to the practice rather than the
practice to the decision.

This page exists because until it, the publication procedure lived ONLY in
decisions. A decision executed by an agent's memory rather than by a mechanism
is not executed, and those five sessions are the evidence.

RU mirror: [`../ru/publishing.md`](../ru/publishing.md).

## Which is which

| Line | What it is | What lives there |
|---|---|---|
| `origin` — GitLab | The development line | The full history: branches, waves, the project's own accounting. Every push goes here and every push builds CI (fast lane in stage `test`, full lane in `test-full`). |
| `github` — GitHub | The release mirror | Releases only, as FLATTENED snapshots. Measured in #189: 16 commits against 405 on `origin/main`. The two lines share no history — `git merge-base` is empty and the roots differ. |
| `tausik/site` — GitLab | The tausik.tech site | A separate repository (VitePress, build, nginx, the site's own CI). Neither core nor the public line carries a trace of it — measured over both trees in session #255 at zero, and `tests/test_site_lives_elsewhere.py` holds the zero (decision #368). A link to tausik.tech in the README is a pointer to the site, not a trace of it. |

One practical rule follows, worth remembering verbatim: **`git push github
v1-9-wave` is not a synchronisation — it carries 431 commits of the private
archive into the public line.** Publication is an act upon the TREE, not upon a
commit (decision #260).

## The publication procedure (decision #368)

GitLab keeps the whole history; GitHub receives **only the tag of the final
version** — a flattened snapshot of the FILTERED tree, committed as a
fast-forward child on top of the confirmed public head. "GitLab is identical
to GitHub" means: the snapshot's content equals the filtered tree of the tag,
byte for byte, and a machine checks that equality, not a memory.

1. The release is assembled and closed on the development line (GitLab); the
   full lane is green by the CI procedure (`.gitlab-ci.yml`: clone,
   `bootstrap --no-detect --ide all`, `pytest -m ''`).
2. The snapshot is built and verified by code — `scripts/publication_snapshot.py`,
   the `tausik publish` command:

   ```bash
   # what goes in, what stays, the leak classes on the snapshot; no commit written
   tausik publish snapshot --from v1.9.0 --parent github/main --dry-run
   # the snapshot on top of the public head; prints the three checks and the next commands
   tausik publish snapshot --from v1.9.0 --parent github/main
   # "identical": the snapshot's tree == the filtered tree of the source
   tausik publish verify --snapshot <sha> --from v1.9.0
   ```

   The command acts on OBJECTS: the working tree, the index, branches and
   remotes are not touched. It refuses when a leak class on the snapshot is not
   zero, when `--parent` is not a commit, or when the snapshot does not equal
   the filter. What it cannot know is the REMOTE's tip: a stale local
   `github/main` is caught by git's fast-forward-only push in step 3, and the
   answer to that refusal is to fetch and rebuild the snapshot on the new tip.
   Force is not a flag the command has — and the firewall forbids it anyway.
3. Push and tag are the owner's acts, by hand, after reading what the command
   printed: `git push github <sha>:refs/heads/main` (fast-forward only), then
   `git push github <sha>:refs/tags/v1.9.0` — a **refspec push**, not a second
   `git tag -a`: the name `v1.9.0` already names the release commit on the
   development line (that is what step 2 built from), and git refuses to
   create it twice. One name, two objects — the release commit on GitLab, the
   snapshot on GitHub — and one filtered tree, which `publish verify` proved
   equal. `tests/test_publish_cli.py` runs the printed acts against a bare
   remote and holds that the remote's `main` and tag land on the snapshot
   while the local name stays on the history. GitHub's tag is LIGHTWEIGHT
   (a ref, no tag object, no message — the annotated tags up to 1.8.0 were
   cut on the orphan line by hand); the release notes are the CHANGELOG and
   the GitHub Release, and `published_tags.json` records the commit either
   way. In the same pass, on the development line, `tausik/published_tags.json`
   is updated (see "Tags" below).
4. External authorship survives: a contributor's commits land by merge or by a
   squash carrying their `Co-Authored-By` — otherwise the authorship is erased.

## What is published: a filter, not the whole tree

Before #368 EVERYTHING git tracked went out, `tausik/` included — the
project's own accounting. Measured in session #251: `github/main` carried
2438 files of `tausik/` out of 3576, 70 % of what a consumer cloned — and the
two leak classes declared below as a remainder lived in that accounting.

The exclusions are now ONE declared constant,
`publication_snapshot.EXCLUDED_FROM_PUBLIC_SNAPSHOT`, held by
`tests/test_publication_snapshot.py`:

| Stays on the development line | Why |
|---|---|
| `tausik/tasks/`, `tausik/stories/`, `tausik/epics/`, `tausik/decisions/`, `tausik/memory/`, `tausik/graph-snapshots/` | the state projection that carries state between machines on a branch; of no use to a consumer of the framework |
| `TODO.md`, `TAUSIK-plan-1.9.md` | internal working documents |
| `.gitlab-ci.yml` | the development line's pipeline |

The ratchet files `tausik/*.json` (`gates`, `policy`, `published_tags`,
`spec_coverage`) **travel**: gates and tests read them. Measured on the 1.9
tree: 1308 files go out, 3090 stay.

The leak classes are still checked by machine — over the WHOLE tree
(`tests/test_publication_lines.py`) and over the SNAPSHOT (`tausik publish
snapshot` refuses on a non-zero class). Measured in session #256:

| Class | Was (#180) | Whole tree | Snapshot | Status |
|---|---|---|---|---|
| A local path carrying the user's name | 12 files | **0** | **0** | cleaned, held by a ratchet |
| Another client's project name | 44 files | **0** | **0** | cleaned, held by a ratchet |
| The internal host `gitlab.yumash.ru` | 17 files | 4 files | **0** | remainder declared on the tree, zero on the snapshot |
| A dev-machine path such as `D:\Work` | not measured | 22 files | **0** | remainder declared on the tree, zero on the snapshot |

The remainder on the whole tree lives in the accounting that does not go out;
its count is pinned and growth is red. On the snapshot both classes are zero,
and that is a refusal by the command, not a declaration.

A file that DESCRIBES a leak — this page, the task about it, the decision, the
test itself — is not a leak. Otherwise the check would forbid writing about the
problem, which costs more than the problem.

## Tags: a published tag is a promise, not a bookmark

The README tells consumers to add this repository as a git submodule, and a
submodule is pinned by SHA or by tag. Moving a published tag therefore relocates
SOMEBODY ELSE'S pin onto a different tree, silently. Force-push is already
refused here on the same reasoning, and git itself declines to overwrite a tag
with "would clobber existing tag". So:

**a published tag is never moved, never deleted, never re-cut.**

### What was measured (session #233, `git ls-remote` on both lines)

| | public (github) | private (origin) | local |
|---|---|---|---|
| tags | 9 | 17 | 22 |

Only on origin: `v1.1.0` `v1.2.0` `v1.3.0` `v1.3.2` `v1.3.7` `v1.4.0` `v1.4.1`
`v1.4.2` `v1.5.2`. Only on github: `v1.5.3`.

Eight names exist on both, and **all eight point at DIFFERENT objects** — not one
of them agrees:

| tag | github | origin |
|---|---|---|
| `v1.5.5` | `8084cc9f` | `c61bbb10` |
| `v1.5.6` | `f380a2e0` | `698f2d00` |
| `v1.5.7` | `7c311e81` | `7eb40153` |
| `v1.5.8` | `49dcf47d` | `e4f961b0` |
| `v1.6.0` | `c50c6de9` | `af283bdf` |
| `v1.6.1` | `e036321d` | `cdde825a` |
| `v1.7.0` | `bf13a09e` | `2ec833a5` |
| `v1.8.0` | `623fb4ee` | `3866702f` |

The cause was measured rather than assumed: the public tags were cut on an orphan
snapshot that shares no ancestor with the real history. The same release number
names two different trees — and before 1.9 a tag name is NOT a shared address
between the lines.

### What is done about it

The past is not repaired: the thirteen missing tags are NOT backfilled and the
eight divergent ones are NOT reconciled. Either action would relocate somebody
else's pin.

The divergence is declared by this table and held by a mechanism:
`tausik/published_tags.json` carries the nine name→object pairs taken from the
public line, and `tests/test_published_tags_are_promises.py` compares a live
`ls-remote` against them. Changing, vanishing AND appearing all count as
movement. An unreachable remote produces a SKIP with its reason, never a green: a
check that passes without reaching the remote asserts what it never measured.

### The publication step added in 1.9

From 1.9 the two objects behind one name are the MODEL, not an accident
(decision #368): the name on the development line names the release commit
with its history, the name on GitHub names the snapshot of that commit's
filtered tree, and the trees agree under the filter by `publish verify`. What
was an unexplained divergence in the eight rows above is a stated relation
from `v1.9.0` on. `tausik/published_tags.json` is updated on the development
line **in the same pass as the push**, as the commit right after it: the
snapshot cannot carry its own sha, so the copy of that file inside the snapshot
is by construction one release behind — a consumer's clone has no remote named
`github`, and the promise check skips there with its reason rather than
asserting a comparison it never made.

## See also

- [`security-checklist.md`](security-checklist.md) — what is checked before anything goes out
- [`sessions.md`](sessions.md) — where decisions such as #267 are recorded
