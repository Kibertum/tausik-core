**English** | [Русский](../ru/start-here-maintainer.md)

# Start here: you are changing TAUSIK itself

<!-- doc-map: reader=maintainer; zone=getting-started -->

You are editing the framework, not using it: a gate, a hook, a generator, a document that other
documents depend on. This page is the reading order for that, and the one habit it asks for is
the project's own: a rule that is only asked for gets switched off the same week, so anything
you add here comes with the mechanism that holds it.

## The order

1. **[architecture.md](architecture.md)** — the layers and what may import what. A change that
   crosses a layer is a design decision, not a refactor.
2. **[testing-principles.md](testing-principles.md)** — scoped pytest, what deserves a test, and
   the anti-patterns this project has already paid for.
3. **[hooks.md](hooks.md)** and **[enforcement-coverage.md](enforcement-coverage.md)** — where
   enforcement lives and exactly where it ends.
4. **[dev-doc-checks.md](dev-doc-checks.md)** — the audits that read the tree: orphan files,
   stale docs, unused Python, duplicate test shapes.
5. **[i18n-strategy.md](i18n-strategy.md)** — both language halves are one document. A
   one-language page must declare why, machine-readably, or the parity check reddens.

## Before you add a rule

- **Put it where it will be read.** A registry kept away from its subject carries an excuse
  nobody re-reads: the singleton list in this repository explained a missing English contract
  with a reason that had been false for years.
- **Give it a ratchet, not a paragraph.** `tausik/gates.json` holds the thresholds; a test reads
  them and refuses growth. Take the threshold AFTER the cleanup — on the numbers before it, a
  ratchet freezes the rubbish.
- **Keep it out of the deselected lane.** `addopts` carries `-m 'not slow'`, so a guard marked
  slow holds its zero only in a lane nobody runs by habit.
- **Name the blind spot.** If the new check cannot see something, say so in its docstring and in
  [known-limitations.md](known-limitations.md). A guard whose blind spot is undocumented reads
  as total.

## Adding a page

Declare its reader and zone in the page itself
(`<!-- doc-map: reader=…; zone=… -->`), write both language halves, and reissue the map with
`python scripts/doc_map.py --write`. A page with no declaration is a finding, not a default.

## Releasing

[publishing.md](publishing.md) for the public snapshot and what is filtered out of it,
[senar-compliance-matrix.md](senar-compliance-matrix.md) for what is claimed against the
standard and what is merely implemented.
