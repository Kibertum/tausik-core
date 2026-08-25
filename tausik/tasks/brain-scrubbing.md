---
slug: brain-scrubbing
title: "Pre-write scrubbing linter: защита \"сути проектов\""
status: done
epic: shared-brain
story: brain-tausik-integration
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_scrubbing.py (new), tests/test_brain_scrubbing.py (new)"
scope_exclude: "scripts/brain_config.py (only READ private_url_patterns / project_names), agents/claude/mcp/brain/** (write-tools task), any Notion I/O (write-tools task)"
relevant_files:
  - "scripts/brain_scrubbing.py"
  - "tests/test_brain_scrubbing.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T08:48:35Z"
---

## Goal

Pre-write scrubbing linter module (scripts/brain_scrubbing.py). Pure functions, no I/O. Four detector families: filesystem paths (leak project location), emails, configured private URL patterns, project-name blocklist (substring match). Each match has severity=block (refuse write) or severity=warn (store with needs_review flag). Public API: scrub(content, blocklist, url_patterns) → ScrubResult; scrub_with_config(content, cfg) wraps it. Called by write-tools before hitting Notion.

## Acceptance Criteria

1) scrub(content: str, *, project_names: list[str], private_url_patterns: list[str]) returns {"ok": bool, "issues": [Issue]} where Issue = {"detector", "severity", "match", "hint"}.
2) 4 detectors: filesystem_paths (Windows D:\\Work\\... + POSIX /home/user/... /Users/...), emails (RFC5322-ish regex), private_urls (compiled regexes from config), project_names_blocklist (case-insensitive substring).
3) Severity: filesystem_paths + emails + private_urls = block; project_names_blocklist = block; no warn-only detectors in v1 (can add later).
4) scrub_with_config(content, cfg: dict) reads blocklist from cfg['project_names'] and patterns from cfg['private_url_patterns'], returns same ScrubResult. Empty/missing fields → no detectors of that type fire.
5) Pure function — no Notion calls, no file I/O, no network. Testable deterministically.
6) Hint messages are actionable: "Remove absolute path '/home/alice/work/proj'; use relative path or remove."
7) ≥20 tests in tests/test_brain_scrubbing.py covering each detector positive + negative, empty content, empty config, unicode, and a "clean content" happy path.
8) mypy + ruff clean on new files; full suite passes.
9) Out of scope: write-tools integration (separate task), task-slug detection (future — can be added as a detector), UI/markdown rendering of issues.

## Plan

[{"step": "Design detector table \u2014 regex patterns for paths / emails, how to compose url_patterns from config, case-insensitive blocklist substring match", "done": true}, {"step": "Implement scripts/brain_scrubbing.py: 4 detectors, scrub() and scrub_with_config() public API, Issue dataclass-like dict", "done": true}, {"step": "Write tests/test_brain_scrubbing.py: \u226520 cases \u2014 each detector + negative + empty config + unicode + clean content", "done": true}, {"step": "Run mypy + ruff on new files; full pytest suite", "done": true}, {"step": "Log AC evidence; task done", "done": true}]

## Rollback

## Journal

- 2026-04-23T08:45:18Z [implementation] — AC verified: 1. scrub API ✓ test_issue_shape_has_required_keys 2. 4 detectors ✓ posix/windows/emails/private_urls/blocklist all tested 3. severity=block ✓ 4. scrub_with_config reads cfg ✓ test_scrub_with_config_reads_fields 5. pure function ✓ no I/O imports 6. actionable hints ✓ asserted in test_posix_home_path_blocked etc 7. 30 tests (≥20) ✓ 8. mypy + ruff clean, 1362 pass ✓ 9. scope held, no write-tools integration ✓
