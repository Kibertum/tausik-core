---
slug: svc-fixtures-need-brain-config-load-brain-stub-when-project
title: "svc fixtures need brain_config.load_brain stub when project has brain enabled"
type: gotcha
tags:
  - brain
  - fixtures
  - isolation
  - regression
  - testing
task: null
edges: []
---

After v1.3.2 enabled brain in this project's `.tausik/config.json`, any test fixture that constructs `ProjectService` and calls `decide()` (or anything that goes through `service_knowledge.decide` → brain_classifier → brain_runtime.try_brain_write_decision) will route writes to the live Notion brain instead of the local SQLite fixture, leaving `decisions()` empty and assertions failing with `IndexError` / `assert N >= M`. Fix: every `svc` fixture must `monkeypatch.setattr(brain_config, "load_brain", lambda: {"enabled": False})` to force local routing. Files that needed this fix: tests/test_service_knowledge_decide.py (v1.3.2), tests/test_edge_cases.py + tests/test_e2e_workflow.py (v1.3.3 follow-up). For tests that DO need brain enabled, override per-test with `with patch("brain_config.load_brain", return_value=brain_cfg)`.
