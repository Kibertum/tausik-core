# TAUSIK 1.11.5 — bounded L3 review

Automatic normal-L3 review is now bounded to one full cohort round and at most
one delta round for red or affected tasks. Unchanged green results carry
forward instead of being reviewed again after every repair.

If round 2 still has blocking findings, TAUSIK stops at an explicit owner
decision. It never schedules an automatic round 3. CRITICAL findings and
configured hard floors remain non-waivable; explicit `/review --deep` remains
available outside the automatic closure budget.

Every round is bound to one immutable issued packet and its digest. CLI and MCP
share strict validation, reviewer separation uses trusted per-task provenance,
and the external reviewer has mechanically enforced Read/Grep-only access.

The acceptance scenario reports exact protocol counts:

| Tasks | Previous calls | Bounded calls | Avoided green re-reviews |
|---:|---:|---:|---:|
| 1 | 2 | 2 | 0 |
| 2 | 4 | 2 | 1 |
| 5 | 10 | 2 | 4 |

These are a worked protocol model, not measured or historical token savings. External
reviewer latency and token telemetry were unavailable and were not estimated.

Full details: [CHANGELOG.md](https://github.com/Kibertum/tausik-core/blob/v1.11.5/CHANGELOG.md) and
[bounded L3 contract](https://github.com/Kibertum/tausik-core/blob/v1.11.5/docs/en/review-cohort-contract.md).

- [English release notes](https://github.com/Kibertum/tausik-core/blob/v1.11.5/docs/en/whats-new-1.11.md)
- [Русские заметки о выпуске](https://github.com/Kibertum/tausik-core/blob/v1.11.5/docs/ru/whats-new-1.11.md)
