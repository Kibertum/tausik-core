---
slug: adversarial-review-mode
title: "Adversarial-review режим в /review"
status: done
epic: claude-hardening
story: p2-quality-loops
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/skills/review/agents/critic.md (новый), agents/skills/review/SKILL.md (обновление), tests/test_adversarial_review_mode.py (новый)"
scope_exclude: "Другие review agents (quality/implementation/testing/simplification/documentation) — не трогать. Другие skills — не трогать."
relevant_files:
  - "agents/skills/review/agents/critic.md"
  - "agents/skills/review/SKILL.md"
  - "tests/test_adversarial_review_mode.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T22:50:58Z"
---

## Goal

/review получает adversarial-subagent: "найди 3 слабых места в этом коде/логике". Свежий взгляд без контекста автора. Из vc.ru + memory #25

## Acceptance Criteria

1) Новый файл agents/skills/review/agents/critic.md — спецификация adversarial-критика с промптом "найди 3 слабых места в предложении/коде автора". 2) SKILL.md обновлён: critic добавлен в таблицу parallel agents (6 агентов вместо 5). 3) Старый раздел "Adversarial Mode" упрощён (или удалён) т.к. критик теперь всегда запускается. 4) test_adversarial_review_mode.py проверяет: (a) файл critic.md существует, (b) содержит ключевые фразы про "3 weaknesses" / "3 слабых места", (c) SKILL.md упоминает critic в таблице, (d) общее число parallel agents теперь 6. 5) pytest all passed. 6) ruff clean. Negative: (a) отсутствие критика в SKILL.md → тест падает (гарантия не потерять). (b) если critic.md пуст → тест падает. (c) изменения не ломают другие тесты.

## Plan

[{"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c agents/skills/review/agents/critic.md \u2014 adversarial subagent spec", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c agents/skills/review/SKILL.md \u2014 critic \u0432 \u0442\u0430\u0431\u043b\u0438\u0446\u0443, \u0443\u043f\u0440\u043e\u0441\u0442\u0438\u0442\u044c Adversarial Mode \u0441\u0435\u043a\u0446\u0438\u044e", "done": true}, {"step": "tests/test_adversarial_review_mode.py", "done": true}, {"step": "pytest + ruff", "done": true}, {"step": "log + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T22:44:51Z [implementation] — AC verified: AC1 (critic.md создан) ✓ — agents/skills/review/agents/critic.md, 6 hunting grounds, stop condition, output format [C1][C2][C3]. AC2 (critic в таблице parallel agents) ✓ — test_skill_agent_table_includes_critic_row + test_skill_says_six_agents passed, SKILL.md обновлён "6 specialized review agents". AC3 (старый Adversarial Mode упрощён) ✓ — секция переработана: adversarial теперь built-in (всегда), "deep" triggers двойной проход критика. AC4 (тесты passed) ✓ — tests/test_adversarial_review_mode.py, 9 тестов: TestCriticAgentFile (5) + TestSkillRegistration (4). AC5 (pytest) — запускаю. AC6 (ruff) ✓ — All checks passed. Negative: (a) отсутствие critic в SKILL.md → тесты упадут. (b) пустой critic.md → тесты упадут. (c) изменения в SKILL.md не ломают структуру.
