**English** | [Русский](../ru/assurance.md)

# Residual assurance contract

<!-- doc-map: reader=user; zone=core-surface -->

TAUSIK derives review depth from residual uncertainty after available evidence,
not from a technology name, file extension, role, or gate name. The canonical
review dispatcher turns this decision into the route consumed by task packages,
the CLI, MCP, and every generated host skill.

## Declarations

Tasks may store `assurance_profiles` as a JSON list and `assurance_impact` as a
JSON object. Stack declarations expose the same keys as defaults. Task profiles
are added to stack profiles; task impact values override stack defaults.

| Profile | Required evidence capabilities |
|---|---|
| `declarative` | `behavior`, `idempotence`, `rollback`, `postconditions` |
| `executable` | `behavior`, `rollback`, `postconditions` |
| `migration` | `behavior`, `rollback`, `postconditions` |
| `research` | `reproducibility`, `provenance` |

Impact axes are `level` (`low`, `medium`, `high`), `blast_radius` (`local`,
`bounded`, `broad`), `reversibility` (`reversible`, `conditional`,
`irreversible`), `security_boundary`, `governance_boundary`, `privileged`,
`data_change` (`none`, `non_destructive`, `destructive`), and
`owner_escalation`. Missing principal axes remain `unknown`; unknown metadata
falls back to L2.

## Evidence capabilities

A gate may declare `evidence_capabilities` in `stack.json`: `syntax`, `schema`,
`policy`, `behavior`, `idempotence`, `rollback`, `postconditions`,
`reproducibility`, or `provenance`. Only a passed gate in the latest signed
receipt contributes its declared capabilities. A gate name proves nothing by
itself.

Lint and schema validation therefore do not prove behavior, idempotence,
rollback, postconditions, or policy compliance. Those capabilities require
gates that actually exercise the property.

## Selection

The pure policy returns profiles, impact, required and observed evidence,
residual gaps, depth, deterministic reasons, and any hard floor.

- L1 requires complete evidence plus low, local, reversible impact.
- L2 covers incomplete metadata, ordinary residual gaps, or fully evidenced
  but elevated contextual impact.
- L3 applies when elevated impact retains uncovered properties.
- L3 is a non-downgradable floor for security or governance boundaries,
  privileged changes, irreversible changes, destructive data migrations, and
  explicit owner escalation.

## Review execution

The task package includes `review_route` and its missing inputs. L1 runs the
selected profile checklists and deterministic gates with zero reviewer calls.
L2 runs one focused reviewer in a fresh context. Normal L3 runs one external
reviewer from a different model family. Separate context on the author's model
is L2, never L3. Multi-agent L3-deep is reserved for an explicit `/review` or a
configured `review.extreme_hard_floor` on an L3 hard-floor task.

Review records persist the actual level, selected profiles, reasons, hard
floor, author and reviewer models, context, invocation count, route, and usage
available for the task. HIGH or CRITICAL findings do not satisfy the passing
L3 closure gate. A substantive repair needs fresh deterministic verification.

## Extension and compatibility

Add a custom stack under `.tausik/stacks/<name>/stack.json` and declare profiles,
impact defaults, and gate capabilities there. A Puppet-like custom stack with
the `declarative` profile is evaluated identically to a built-in declarative
stack; no central allowlist or routing branch is needed.

The database change is additive. Existing tasks and stacks have no declarations,
which yields conservative L2 rather than fabricated L1 or blanket L3. Fresh and
upgraded databases carry the same nullable task columns.
