# TAUSIK 1.11.4

TAUSIK 1.11.4 repairs the security-sensitive verification-close deadlock and
hardens the public-release boundary. A green security run remains
non-replayable, but now issues one signed, single-use proof whose project,
files and live gate configuration are rechecked at task closure.

Verification identity and policy are now structured instead of inferred from
command text. The affected-test selector covers every changed source, proof
signatures include complete gate applicability, comment-reference evidence
survives intermediate commits, and repeated framework friction files one
redacted, idempotent local task.

Release tags now wait for CI on the exact public snapshot SHA. Publication
audits the candidate tree and all reachable ancestors, supports parentless
recovery, and verifies remote refs anonymously. The authorized 1.11.3
containment moved GitHub `main` and `v1.11.3` to parentless snapshot `3dd6f5d`,
deleted `v1-11-3`, and audited all 16 advertised refs; none reaches the
contaminated commits.

Read the exact 1.11.4 changes and bilingual 1.11-series overview:

- [Exact 1.11.4 changelog](https://github.com/Kibertum/tausik-core/blob/v1.11.4/CHANGELOG.md)
- [English 1.11 overview](https://github.com/Kibertum/tausik-core/blob/v1.11.4/docs/en/whats-new-1.11.md)
- [Russian 1.11 overview](https://github.com/Kibertum/tausik-core/blob/v1.11.4/docs/ru/whats-new-1.11.md)
