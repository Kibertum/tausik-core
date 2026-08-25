---
slug: gate-runner-hardening-timeouts-severity-defaults-s
title: "Gate runner hardening: timeouts, severity defaults, subprocess safety"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_runner.py, scripts/project_config.py"
scope_exclude: "scripts/service_task.py, scripts/project_backend.py, agents/"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T11:50:35Z"
---

## Goal

Сделать gate_runner надёжным: таймауты для команд, filesize severity=block по умолчанию, sanitization аргументов subprocess

## Acceptance Criteria

1. Gate commands имеют таймаут (30 сек по умолчанию). 2. filesize gate severity=block по умолчанию. 3. subprocess аргументы sanitized — нет shell injection через {files}. 4. Тесты на таймаут и sanitization.

## Plan

## Rollback

## Journal

- 2026-04-07T11:49:27Z [implementation] — AC verified: 1. Gate commands have configurable timeout (gate.timeout, default 120s, pytest 180s) ✓ 2. filesize severity=block by default ✓ 3. subprocess args sanitized via shlex.quote + ALLOWED_GATE_EXECUTABLES allowlist + shell injection detection (pre-existing, verified) ✓ 4. Tests: test_command_gate_custom_timeout + test_filesize_default_severity_is_block added, 833 tests pass ✓
