---
slug: enterprise-stack-agnostic
title: "Enterprise stack-agnostic QG-2 — fix silent bypass + verticals"
status: done
---

Critical bug fix: pytest gate silently passes на Go/PHP/Rust проектах (file_extensions filter возвращает empty → "skipped — pass" → QG-2 green). Plus добавление реальных test runner gates для Go/Rust/PHP/JS/TS + IaC stacks (Ansible/Terraform/Helm/K8s/Docker) с honest scope ("lint-only" для IaC). Pre-empts misleading enforcement claim для 14+ declared stacks.
