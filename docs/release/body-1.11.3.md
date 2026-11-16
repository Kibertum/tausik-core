# TAUSIK 1.11.3

TAUSIK 1.11.3 is the verification-economy and Kilo-completion release. Track A
ships pooled verification end to end — `verify --tasks` / `--story` / `--epic`,
the cohort contract, a live 34→1 verify-execution proof on this release's own
work, and the close/recovery paths fixed from production reds. The economy
claim is measured, not promised: repeated-prefix bytes −30.65% against the
frozen 63,333-byte baseline, natural accepted-task response-round median 17
(attributable) / 25 (upper bound) against a baseline of 89 and a target of ≤40;
the verification-cycle replay is resolved by refusal — its savings are not
claimed.

Kilo is now a fully governed host: alongside the 1.11.2 gate plugin and model
observation, the second extension point — the `permission` surface — is used
(host-level deny on editing `.tausik/tausik.db` and `.kilo/plugins/*`, ask on
`git push*` and `sqlite3*`, deny on `external_directory`), and vendor agents
are normalized at the deploy boundary so the 1.11.2 fix can no longer be wiped
by a redeploy.

The framework also reads itself: `doctor --harness-audit` re-reads the
installed state, `doctor --friction` files agent-friction drafts (its first
production catch: a 105-refusal `cost_usd=None` bug), a blocked task now
carries its question as fields and `status` leads with it, and the memory tail
selects by significance, not just recency.

Read the exact 1.11.3 changes and the bilingual 1.11-series overview:

- [Exact 1.11.3 changelog](https://github.com/Kibertum/tausik-core/blob/v1.11.3/CHANGELOG.md)
- [English 1.11 overview](https://github.com/Kibertum/tausik-core/blob/v1.11.3/docs/en/whats-new-1.11.md)
- [Russian 1.11 overview](https://github.com/Kibertum/tausik-core/blob/v1.11.3/docs/ru/whats-new-1.11.md)
