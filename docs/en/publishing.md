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

## The publication procedure

1. The release is built and closed on the development line (GitLab).
2. Publication goes out as a **fast-forward child** on top of the confirmed
   public head, built with `commit-tree` over the release tree. Force is refused
   by the firewall and is not a fallback.
3. External authorship survives: 1.9 lands on `main` as a merge of `release/1.9`
   or as a squash carrying `Co-Authored-By` for the author of PR #5 — otherwise
   the attribution is erased.

## Precondition: what goes out with the tree

Publication carries the WHOLE tracked tree, `tausik/` — the project's own
accounting — included. So what is checked before publishing is not "did we
forget anything" but named classes of leak, and it is checked by machine.

Measured in session #233 over 4,208 tracked files (not recalled from #180):

| Class | Was (#180) | Now | Status |
|---|---|---|---|
| Local path carrying the user's name | 12 files | **0** | cleaned, held by a ratchet |
| Other clients' project names | 44 files | **0** | cleaned, held by a ratchet |
| Internal host `gitlab.yumash.ru` | 17 files | 5 files, 8 occurrences | declared remainder; growth is red |
| Dev-machine path such as `D:\Work` | not measured | 39 files, 81 occurrences | declared remainder; growth is red |

The first two are held at zero: their return to a tracked file turns
`tests/test_publication_lines.py` red. The last two are NOT cleaned — they are
weaker (a directory layout and an internal server address, not an identity) and
live mostly inside the project's own accounting. Their counts are pinned, and
growth is red too: the gap is declared rather than quietly closed.

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

The release tag is cut on the public line **as part of the publication**, in the
same pass as the publication commit, and `tausik/published_tags.json` is updated
in that same commit. Otherwise the next name diverges exactly as the previous
eight did — not through malice, but because nobody remembered.

## See also

- [`security-checklist.md`](security-checklist.md) — what is checked before anything goes out
- [`sessions.md`](sessions.md) — where decisions such as #267 are recorded
