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

## What this page does not settle

The tag divergence between the lines. Measured in #189: same-named tags point at
DIFFERENT commits (`v1.8.0` is `623fb4ee` on GitHub and `3866702f` on origin),
plus tags that exist on one side only. That is the separate open task
`tags-diverged-between-the-public-and-the-private-line`, and until it closes a
tag name is not a shared address between the two lines.

## See also

- [`security-checklist.md`](security-checklist.md) — what is checked before anything goes out
- [`sessions.md`](sessions.md) — where decisions such as #267 are recorded
