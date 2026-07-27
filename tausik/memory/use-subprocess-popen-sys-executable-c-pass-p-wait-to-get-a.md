---
slug: use-subprocess-popen-sys-executable-c-pass-p-wait-to-get-a
title: "Use subprocess.Popen([sys.executable, '-c', 'pass']); p.wait() to get a freshly-dead PID for _unused"
type: dead_end
tags: []
task: cleanup-v136
edges: []
---

Approach: Use subprocess.Popen([sys.executable, '-c', 'pass']); p.wait() to get a freshly-dead PID for _unused_pid() in lock tests
Reason: Hung on Windows GitHub runners (Popen.wait blocked indefinitely — likely AV scanning the spawned python or Windows-specific subprocess overhead). Worked fine on macOS+Ubuntu but blocked the same Windows lock tests it was supposed to fix. Replaced with `return 0` which hits the `pid <= 0` early-return inside _pid_alive — same lock-reclamation code path exercised, no OS-level kill call, no subprocess spawn. Lesson: when fixing CI, prefer the simplest path that exercises the code under test rather than a "more realistic" mechanism that adds platform-dependent behavior.</reason>
<parameter name="tags">["windows", "ci", "subprocess", "tests"]
