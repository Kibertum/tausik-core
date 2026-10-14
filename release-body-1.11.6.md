# TAUSIK 1.11.6 — one model family per environment

SENAR Rule 4 no longer requires the L3 reviewer to run on a different model
family. Separation of duties now holds by the isolated, mechanically
read-only reviewer context: the reviewer runs on the SAME model family as
the author — the model the host already runs.

One family per environment: a Claude host reviews with Claude only, Codex
with GPT only, z.ai with GLM only. Pulling another family for review is
prohibited and enforced — an L3 record with a cross-family reviewer is
refused, while same-family records (including the author's own model) are
the recordable form. Both model identities remain mandatory on every L3
record.

The pre-1.11.6 `different-model` context token stays readable, so historical
review records remain valid; new rounds record `external`. Schema v81 widens
the cohort-round CHECK by a guarded table rebuild. The external-reviewer
subagent drops its hardcoded model and now blocks a delegation that asks for
another family instead of one matching its own.

Also fixed: the bounded task-context package could return a few bytes over
its budget when the omission marker itself crossed the ceiling — whole-unit
omission now swallows the marker, and a boundary test sweeps the budgets.

Full details: [CHANGELOG.md](https://github.com/Kibertum/tausik-core/blob/v1.11.6/CHANGELOG.md) and
[SENAR rules](https://github.com/Kibertum/tausik-core/blob/v1.11.6/docs/en/senar.md).

- [English release notes](https://github.com/Kibertum/tausik-core/blob/v1.11.6/docs/en/whats-new-1.11.md)
- [Русские заметки о выпуске](https://github.com/Kibertum/tausik-core/blob/v1.11.6/docs/ru/whats-new-1.11.md)
