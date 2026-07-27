---
slug: v15-aidd-autogen
title: "AIDD: autogen vision.md from existing code"
status: done
epic: v15-cross-ide-parity
---

v1.5 follow-up to v14b-aidd-scaffold-basic. Inspect repo structure (file tree, manifests, top docstrings), call LLM to draft a vision.md outlining target user + core experience based on what the code actually does. Idempotent — re-runs detect drift.
