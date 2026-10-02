---
slug: pr-into-awesome-harness-engineering
title: "PR в awesome-harness-engineering: нас там ноль упоминаний"
status: planning
epic: release-113-evidence
story: release113-outward
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "docs/**"
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#119"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

TAUSIK присутствует в курируемой карте дисциплины, к которой он принадлежит.

## Acceptance Criteria

1. PR подан по их формату: одна строка, описывающая ПАТТЕРН, а не продающая продукт. Их критерии — «addresses a specific harness problem: permissions, memory, verification», vendor-agnostic.
2. Проверено перед подачей: упоминаний TAUSIK в их README ноль (подтверждено grep 12.08.2026).
3. НЕГАТИВНЫЙ сценарий: формулировка, читаемая как реклама, отклоняется их же правилом про product marketing. Текст проверяется на это ДО подачи.
4. НЕГАТИВНЫЙ сценарий: массовая рассылка PR по десяткам awesome-списков ЗАПРЕЩЕНА — это спам-паттерн. Второй список только после того, как первый дал измеримый трафик.

## Plan

## Rollback

PR закрывается

## Journal
