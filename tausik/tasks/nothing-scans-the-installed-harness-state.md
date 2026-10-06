---
slug: nothing-scans-the-installed-harness-state
title: "Никто не сканирует установленную обвязку: мы проверяем входящее и не смотрим на то, что уже лежит"
status: planning
epic: release-1-11-3
story: release1113-quality-ratchets
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/service_doctor*.py"
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#98"
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

Установленное состояние обвязки — .claude, MCP-конфиг, память — регулярно проверяется на то, что в него могло приехать: невидимый Unicode, императивы в записях памяти, дрейф хуков от исходников.

## Acceptance Criteria

1. `tausik doctor --harness-audit` — детерминированный скан установленного состояния: развёрнутые профили IDE, MCP-конфиги, записи памяти. Без LLM и без сети.
2. Проверки переиспользуют существующее: install-guard невидимого Unicode, детектор секретов, сравнение с исходниками в harness/. Второй набор паттернов НЕ пишется.
3. Названа асимметрия, которую задача закрывает: подписи и install-guard защищают ВХОДЯЩЕЕ, но после установки состояние никто не перечитывает, а инъекция приезжает именно в него.
4. Записи памяти проверяются на императивные конструкции, адресованные будущему агенту, — память есть неревьюенный контекст, и это надо назвать вслух, а не считать очевидным.
5. Вердикт — WARN, не BLOCK: ложные срабатывания на легитимных императивных записях неизбежны, а гейт, блокирующий работу на своей же памяти, будет отключён целиком.
6. НЕГАТИВНЫЙ сценарий: скан проверен на ПОДСАЖЕННОМ образце — невидимый Unicode в SKILL.md, императив в записи памяти, изменённый развёрнутый хук. Не находит хотя бы один — детектор сломан.
7. НЕГАТИВНЫЙ сценарий: точность на живом проекте. Больше пяти ложных тревог на чистом дереве — порог поднимается или проверка снимается.

## Plan

## Rollback

git revert коммита; подкоманда doctor снимается

## Journal
