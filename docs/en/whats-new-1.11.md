**English** | [Русский](../ru/whats-new-1.11.md)

# TAUSIK 1.11: less context, fewer rounds, the same evidence

<!-- doc-map: reader=user; zone=release-notes -->

TAUSIK 1.11 targets the cost of accepted work in Codex. It reduces repeated
framework context and avoids deterministic model returns without weakening QG-0,
QG-2, verification evidence or fail-open behaviour.

## Measured changes

| Surface | 1.11 result |
|---|---:|
| Repeated MCP prefix, same 147 tools | 63,333 → 42,519 bytes (**−32.9%**) |
| Two reviewed low-value test groups | 87 → 45 nodes (**−48.3%**) |
| Codex cache share in the observed baseline | **97.8%** |
| Default quality lane, public snapshot | 12,559 passed · 100 skipped · 143 deselected |
| Slow quality lane, public snapshot | 129 passed · 14 skipped · 12,659 deselected |

The high cache share means the next useful levers are fewer model rounds and
economical routing, not more blind context deletion.

## What changed

- `/start` is one bounded call. `task start` can return its package, and
  `task show --package` is the normal bounded retrieval path.
- Ordinary verify selects affected tests. Ambiguous, unmapped or sensitive
  changes fail open to the complete applicable lane.
- Verify output is compact, but full logs and machine counts stay under
  `.tausik/verification/`.
- Codex and Kilo usage are read from native local records without storing
  conversation content or double-counting cache/reasoning subsets.
- Routing can choose an economical bounded worker and escalate for named risk;
  it never claims to switch the active coordinator.
- User-facing answers default to controlled prose and use tables or diagrams
  only when they materially reduce reading effort.

## Honest limits

This release does **not** claim that every project will use 30% fewer weekly
Codex credits. Natural accepted-task rounds have not yet met the release target,
Luna is not yet qualified as the routine default, and one verification replay
still loses preflight evidence. Those measurements continue on the 1.11.x line.

## Attribution

The 1.11 work was developed by Andrey Yumashev with OpenAI Codex. Release commits
carry `Co-authored-by: Codex <codex@openai.com>` so GitHub attributes Codex as a
contributor.

See the [full changelog](../../CHANGELOG.md) and the
[Russian release notes](../ru/whats-new-1.11.md).

GitHub Release links:

- [English notes](https://github.com/Kibertum/tausik-core/blob/v1.11.2/docs/en/whats-new-1.11.md)
- [Russian notes](https://github.com/Kibertum/tausik-core/blob/v1.11.2/docs/ru/whats-new-1.11.md)
