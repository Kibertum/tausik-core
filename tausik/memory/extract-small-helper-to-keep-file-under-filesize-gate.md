---
slug: extract-small-helper-to-keep-file-under-filesize-gate
title: "Extract small helper to keep file under filesize gate"
type: pattern
tags: []
task: v14b-status-exploration-audit-signals
edges: []
---

When adding a new method tips a file over the 400-line gate, prefer extracting the BODY to an existing thematic module (e.g. service_session_metrics.py for session/audit metrics) and keeping a thin forwarder method on the original class. Pattern: add `def helper(be: Any) -> int: ...` at module level alongside related helpers, then on the class: `def helper(self) -> int: from module import helper as _f; return _f(self.be)`. This preserves the public API, keeps callers unchanged, and exploits the lazy-import idiom already used elsewhere in project_service.py (search for `from service_session_metrics import`). Worked here: project_service.py 405→397 by moving audit_overdue_sessions body to service_session_metrics.py while keeping `svc.audit_overdue_sessions()` callable.</content>
<parameter name="tags">["filesize-gate", "refactor", "extract-helper"]
