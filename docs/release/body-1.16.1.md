# TAUSIK 1.16.1

Reliable Codex chat completion and advisory host context defaults.

- Codex Stop never forces automatic continuation of an unfinished task.
- Phrase-based Stop detection removed; cached legacy registrations remain safe.
- Context thresholds recommend checkpoints without forcing a new chat by default.
- Old checkpoint guidance migrates on read while preserving history and owner instructions.
- Mutation authorization, native identity, preflight, task budgets and QG gates remain enforced.
- Fixes for shell preflight binding, quoted CLI search arguments, native model attribution and WSL bytecode hygiene.

Update the framework checkout to `v1.16.1`, rerun bootstrap for configured hosts,
then reload the IDE once.

Full notes:
[English](https://github.com/Kibertum/tausik-core/blob/v1.16.1/docs/en/whats-new-1.16.md) ·
[Русский](https://github.com/Kibertum/tausik-core/blob/v1.16.1/docs/ru/whats-new-1.16.md).
