---
slug: subprocess-text-true-decodes-with-cp1252-on-windows-force
title: "subprocess text=True decodes with cp1252 on Windows — force encoding on every CLI/git reader"
type: gotcha
tags:
  - cp1252
  - hooks
  - subprocess
  - unicode
  - v1.5.7
  - windows
task: fix-hook-cp1252-unicode-crash
edges: []
---

subprocess.run(..., text=True) WITHOUT encoding= decodes the child's stdout using the OS locale codec (cp1252 on RU/most Windows). Any Cyrillic/non-cp1252 byte (e.g. UTF-8 0x81, undefined in cp1252) raises UnicodeDecodeError in the reader thread -> result.stdout=None -> a following .strip() raises AttributeError OUTSIDE the caught (TimeoutExpired,FileNotFoundError,OSError) tuple -> the whole hook/gate aborts with a traceback. This silently broke SessionStart on projects whose `tausik memory block`/task titles contain Cyrillic (v1.5.7 fix). RULE: every text=True subprocess reader of CLI/git output MUST pass encoding="utf-8", errors="replace". v1.5.6 fixed only the ENCODE side (PYTHONUTF8/-X utf8 for output); this is the DECODE side. Fixed 12 sites: session_start, _common, auto_format, task_done_verify, session_metrics, check_docs, project_cli_extra, project_cli_renar, pytest_test_count, service_session, verify_git_diff. Guard test: grep text=True in scripts/ and assert encoding= within +/-6 lines.
