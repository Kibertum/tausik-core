---
slug: tausik-verify-github-action-badge
title: "Бейдж проверенной квитанции в чужих пул-реквестах"
status: planning
epic: visibility-stream
story: field-presence
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/**"
  - ".github/**"
  - "docs/**"
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Единственная ось, где TAUSIK первый, а не догоняющий, становится видимым артефактом в чужих репозиториях.

## Acceptance Criteria

1. GitHub Action проверяет ed25519-квитанцию ОФЛАЙН и ставит status check в пул-реквест. Основание хода: криптографической верификации нет ни у claude-mem, ни у ECC, ни у spec-kit — проверено чтением их репозиториев.
2. Action опубликован в GitHub Actions Marketplace и работает в чужом репозитории без установки TAUSIK.
3. Измерено: не менее трёх ВНЕШНИХ репозиториев с бейджем за квартал. Меньше — ход не сработал, и это признаётся, а не объясняется.
4. НЕГАТИВНЫЙ сценарий: поддельная, просроченная и относящаяся к другому коммиту квитанция дают ТРИ РАЗНЫХ отказа, а не один общий.
5. НЕГАТИВНЫЙ сценарий: бейдж НЕ имеет права утверждать больше, чем доказывает квитанция. Формулировка «gates proven, not claimed» верна; «код проверен» или «безопасно» — ложь, и она запрещена.
6. ЗАВИСИМОСТЬ: после однокомандной установки, иначе бейдж ведёт людей на трёхшаговый барьер.

## Plan

## Rollback

Action снимается с Marketplace; ядра не касается

## Journal
