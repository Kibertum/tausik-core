---
slug: render-artifact-output-test-with-a-task-slug-on-the-minimal
title: "Render artifact-output test with a task slug on the minimal _Service fixture"
type: dead_end
tags: []
task: bound-agent-validation-output-to-durable-artifacts
edges: []
---

Approach: Render artifact-output test with a task slug on the minimal _Service fixture
Reason: A task-scoped render also loads signed-receipt state through svc.be; this fixture intentionally supplies only a project root. The artifact contract is task-independent, so the test now uses task_slug=None.
