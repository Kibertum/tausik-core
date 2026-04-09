# Shared Skill Patterns

Common patterns used across multiple skills. Reference this instead of duplicating.

## Session Health Check
```bash
.tausik/tausik session size
```
- CRITICAL → "Run /end or /checkpoint now."
- WARNING → "Consider /end or /checkpoint soon."
- OK → silent

## CLAUDE.md Dynamic Section Update
Replace between `<!-- DYNAMIC:START -->` and `<!-- DYNAMIC:END -->`:
```
Session: #{id} active ({date})
Branch: {branch} | Version: {version}
Backend: CouchDB+Meilisearch (brain) + Raven API Gateway :{port}

Progress: {done}/{total} done + {planning} planning | Epic {epic-slug} active
Tests: {N} ({suites} suites) | Tokens: {M} (${cost}) | Velocity: {SP}/session

Last session (#{prev}): {summary}
Next steps: {slug1}, {slug2}, ...
{IF warnings: Warnings: ...}
```

## Handoff JSON
```json
{"summary":"...","completed":["slug1","slug2"],"in_progress":[],
 "blocked":[],"key_files":["path1"],"dead_ends":[],"next_steps":["slug1 — reason"],
 "warnings":["..."]}
```

## KB Contribution (on task done)
Read `.claude/references/kb-protocol.md` for role-specific minimums.
