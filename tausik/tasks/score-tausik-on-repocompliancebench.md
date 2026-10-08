---
slug: score-tausik-on-repocompliancebench
title: "Внешний бенчмарк дисциплины уже существует — RepoComplianceBench меряет ровно то, что мы продаём"
status: planning
epic: release-113-evidence
story: release113-proof
complexity: medium
role: qa
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#133"
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

arXiv 2607.26819, «A First Look at Coding Agents Compliance with AI Contribution Rules in Open-Source Communities». 106 задач из 49 репозиториев с правилами о вкладе ИИ, четыре передовые модели. Меряются ЧЕТЫРЕ поведения, и это в точности наш предмет: отказ вносить вклад в репозиторий, где ИИ запрещён; правдивое раскрытие ИИ-участия; прохождение требуемых репозиторием проверок; эскалация критических шагов человеку.

НАХОДКИ АВТОРОВ, КОТОРЫЕ ДЕЛАЮТ ЭТО ВЫГОДНЫМ ДЛЯ НАС: агенты НИКОГДА не отказываются вносить вклад в репозиторий с запретом, ни при одном испытанном условии; агенты ПОЧТИ НИКОГДА не запрашивают правила вклада сами; раскрытие и прохождение проверок подтягиваются напоминаниями, а вот принуждение к запрету и эскалация человеку названы ОТКРЫТОЙ ПРОБЛЕМОЙ. Наш хук старта впрыскивает правила ДО первого действия агента, то есть по оси «сам не спрашивает» мы структурно не можем провалиться там, где голый агент даёт ноль.

ЦЕННОСТЬ: это готовое ВНЕШНЕЕ доказательство, чужой линейкой, для единственного обещания, которое фреймворк пока не доказывает. Дешевле собственного бенчмарка и убедительнее его. НЕГАТИВНОЕ: результат публикуется КАКИМ ПОЛУЧИЛСЯ. Плохой счёт по осям запрета и эскалации есть находка о нас, и он идёт в отчёт наравне с хорошим.

## Acceptance Criteria

## Plan

## Rollback

Прогон внешнего бенчмарка и запись результата; кода не трогает. Отката не требуется. Публикация результата наружу — отдельное согласие владельца и в эту задачу не входит.

## Journal
