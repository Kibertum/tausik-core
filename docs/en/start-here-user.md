**English** | [Русский](../ru/start-here-user.md)

# Start here: you are using TAUSIK on your project

<!-- doc-map: reader=user; zone=getting-started -->

You installed TAUSIK, or someone installed it for you, and an agent now refuses to write code
until a task exists. This page is the reading order for that situation. It exists because the
documentation used to be one undifferentiated list: 64 pages in English with no statement of who
each one is for, and the order of reading lived only in the navigation hub.

- [Glossary](glossary.md) — what QG-0, gate, ratchet, projection and the rest of the words mean

Three entry pages exist, one per reader. This is the one for **the person whose project TAUSIK
governs**. If you are an agent working through TAUSIK, read
[start-here-agent.md](start-here-agent.md); if you are changing TAUSIK itself, read
[start-here-maintainer.md](start-here-maintainer.md).

## The order

1. **[quickstart.md](quickstart.md)** — install, initialise, close one task end to end. Nothing
   below makes sense before you have done that once.
2. **[senar.md](senar.md)** — why the refusals exist. TAUSIK enforces a methodology; the gates
   are its rules, not the framework's opinions.
3. **[workflow.md](workflow.md)** — the task lifecycle you will spend your time in: plan, start,
   verify, close.
4. **[cli.md](cli.md)** — the command reference. Skim the headings once so you know what exists;
   do not read it through.
5. **[configuration.md](configuration.md)** — what you can change, and
   [config-trust-tiers.md](config-trust-tiers.md) for which settings a project may override and
   which belong to the machine.

## When something blocks you

A gate that refuses names the check, the cause and the remediation command. Read that line
before searching: it is written to be sufficient.

- **A close is refused** — [quality and verification](../README.md#quality--verification), and
  [receipts.md](receipts.md) for what a signed verification run does and does not prove.
- **A hook refuses a write** — [hooks.md](hooks.md), and
  [enforcement-coverage.md](enforcement-coverage.md) for where the enforcement ends.
- **Something is not guaranteed and you need to know that in advance** —
  [known-limitations.md](known-limitations.md). Every deliberate gap is there with the reason
  it is cheaper to live with than to close.

## What you can skip

The `agent` and `maintainer` pages of the [documentation map](../_generated/doc-map.md). They
are not hidden and nothing breaks if you read them, but they answer questions you do not have:
how an assistant should execute a procedure, and how to change TAUSIK's own machinery.
