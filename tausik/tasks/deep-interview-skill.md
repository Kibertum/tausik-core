---
slug: deep-interview-skill
title: "/interview — Deep Interview скилл (Socratic Q&A перед сложной задачей)"
status: done
epic: claude-hardening
story: p3-nice-to-have
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/skills/interview/SKILL.md (новый), tests/test_interview_skill.py (новый)"
scope_exclude: "Другие skills — не трогать. bootstrap templates — не трогать."
relevant_files:
  - "agents/skills/interview/SKILL.md"
  - "tests/test_interview_skill.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T23:20:32Z"
---

## Goal

Для complex задач — 2-3 уточняющих вопроса (Socratic) перед стартом. Из oh-my-claudecode + prompt-master ("max 3 clarifying questions")

## Acceptance Criteria

1) Новый agents/skills/interview/SKILL.md с YAML frontmatter и алгоритмом Socratic Q&A перед complex задачей (максимум 3 уточняющих вопроса как prompt-master). 2) Скилл триггерится на "interview", "interview me", "уточни", "задай вопросы". 3) Содержит секцию Gotchas (требуется lint). 4) pytest test_interview_skill.py проверяет существование файла и ключевые фразы "Socratic", "3 questions". 5) pytest all passed + lint test на Gotchas не падает. 6) ruff clean. Negative: (a) файл без frontmatter → skill-test fails (существующий тест skills loading). (b) более 3 вопросов в алгоритме → нарушение принципа prompt-master, flagged вручную.

## Plan

[{"step": "agents/skills/interview/SKILL.md + Gotchas", "done": true}, {"step": "tests/test_interview_skill.py", "done": true}, {"step": "pytest + ruff + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T23:17:38Z [implementation] — AC verified: AC1 (SKILL.md создан) ✓ — agents/skills/interview/SKILL.md с frontmatter. AC2 (триггеры) ✓ — "interview me", "уточни", "задай вопросы" в description. AC3 (Gotchas секция) ✓ — test_has_gotchas_section + общий test_every_skill_has_gotchas_section passed. AC4 (pytest) ✓ — 7 тестов test_interview_skill.py, 4 теста lint — все passed. AC5 (gotchas/boilerplate lint тесты зелёные). AC6 (ruff clean). Negative: (a) frontmatter проверяется test_skill_has_frontmatter. (b) "at most 3" принцип явно указан в алгоритме + test_max_3_questions_principle.
