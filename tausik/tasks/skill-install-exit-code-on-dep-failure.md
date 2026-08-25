---
slug: skill-install-exit-code-on-dep-failure
title: "skill install возвращает 0, когда requires не установились — скилл стоит и не работает"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/skill_manager.py (install_skill), scripts/project_cli_skill.py, scripts/service_skills.py при необходимости, tests/"
scope_exclude: "Не менять install_skill_deps. Не трогать MCP-обёртку без нужды."
relevant_files:
  - "scripts/skill_manager.py"
  - "tests/test_skill_manager.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T13:28:05Z"
---

## Goal

Провалить установку громко: ненулевой код возврата CLI и явная ошибка в MCP, когда объявленные в requires зависимости не встали. Сейчас install_skill возвращает строку, CLI печатает её и выходит с 0 — автоматика (CI, MCP-вызовы) считает установку успешной. Это прямое нарушение принципа 'нулевая толерантность к тихим ошибкам'. Решить заодно: оставлять ли скилл установленным. Рекомендация — не активировать скилл и не писать его в installed_skills, раз он заведомо нерабочий.

## Acceptance Criteria

1) install_skill сигналит о неудаче зависимостей так, чтобы вызывающий отличил её от успеха (исключение, а не строка). 2) CLI 'tausik skill install' выходит с ненулевым кодом. 3) Скилл не попадает в installed_skills, если объявленные зависимости не встали. 4) Вердикт подписи и команда ручной доустановки остаются в сообщении. Негативные сценарии: 5) Ошибка, если код возврата 0 при неудаче зависимостей — автоматика примет это за успех. 6) Ошибка, если скилл без requires перестал ставиться. 7) Ошибка, если файлы скилла остались, а конфиг о нём не знает, или наоборот.

## Plan

## Rollback

git checkout -- scripts/ tests/; bootstrap.

## Journal

- 2026-07-10T13:19:41Z [implementation] — AC verified: 1. ✓ install_skill поднимает SkillManagerError вместо возврата строки — test_deps_failure_keeps_signature_verdict, test_install_deps_fail_partial_message. 2. ✓ CLI выходит ненулевым: project.py уже ловит SkillManagerError и делает sys.exit(1) — живой прогон через scripts/project.py дал rc=1 и 'Error: ... was NOT installed' в stderr. 3. ✓ Скилла нет в installed_skills (живой прогон: []), а скопированные файлы удаляются — test_deps_failure_leaves_no_half_install, живой прогон: 'skill dir left behind: False'. 4. ✓ Вердикт подписи и команда доустановки в сообщении: 'UNSIGNED'/'WARNING' + 'pip install <пакеты>' + 'tausik skill install <имя>'. 5. ✓ (негативный) Прежний контракт возвращал строку 'Skill ... installed ... but dependency installation failed' и rc=0; старый тест это и закреплял. Тест переписан: теперь падает, если сообщение читается как успех. 6. ✓ (негативный) test_skill_without_requires_still_installs — обычный путь не задет. 7. ✓ (негативный) test_deps_failure_leaves_no_half_install проверяет обе стороны: ни файлов, ни записи в конфиге. Root cause (logic-error): «нулевая толерантность к тихим ошибкам» нарушалась самим ядром — неуспех кодировался текстом сообщения, а не кодом возврата. Любой потребитель кода возврата (CI, MCP, shell) видел успех. Prevention: неуспех операции выражается типом (исключение) или кодом, никогда — только строкой; и установка атомарна: либо скилл на месте и работает, либо его нет. Файлы удаляются через skill_git.rmtree_force, поэтому откат не спотыкается о read-only. Domain: сквозной прогон вне тестов — scripts/project.py skill install myskill в чистом временном проекте: rc=1, каталог скилла отсутствует, installed_skills пуст.
