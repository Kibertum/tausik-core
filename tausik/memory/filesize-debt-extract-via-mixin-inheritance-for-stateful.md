---
slug: filesize-debt-extract-via-mixin-inheritance-for-stateful
title: "Filesize debt: extract via Mixin inheritance for stateful methods"
type: convention
tags:
  - "filesize,refactoring,mixin,senar"
task: clean-tausik-doctor-warnings-brain-enabled-false-c
edges: []
---

When a class method has too many self.* references and needs extraction for the 400-line filesize gate, prefer adding a new Mixin (e.g. TaskDoneReportMixin) and have the original class inherit from it — preserves IDE typing and method resolution via MRO. Avoid passing the class instance to a free function, that breaks IDE goto-definition. Pattern proven in service_task.py → service_task_done.py during filesize-debt-paydown-2.
