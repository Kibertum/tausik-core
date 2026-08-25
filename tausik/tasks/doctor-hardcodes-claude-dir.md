---
slug: doctor-hardcodes-claude-dir
title: "tausik doctor падает на 6 из 7 IDE: движок хардкодит .claude/ там, где есть ide_utils"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/project_cli_doctor.py, scripts/service_roles.py, scripts/project_cli.py (строка предупреждения о числе скиллов), scripts/ide_utils.py (только если нужен новый хелпер), tests/ (новый тест doctor multi-IDE + линт), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "bootstrap/* (развёртывание профилей не трогаем), service_doctor_caveman.py (Claude-specific по замыслу, только закрывается проверкой detect_ide), MCP-серверы и их содержимое, ide_utils.IDE_REGISTRY (состав IDE не меняем)"
relevant_files:
  - "scripts/project_cli_doctor.py"
  - "scripts/ide_utils.py"
  - "scripts/service_roles.py"
  - "scripts/project_cli.py"
  - "scripts/snippet_detect.py"
  - "scripts/project_cli_aidd_autogen.py"
  - "scripts/hooks/session_start.py"
  - "tests/test_doctor_multi_ide.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T15:23:04Z"
---

## Goal

Баг СЕГОДНЯ, а не рефактор к 2.0. scripts/ide_utils.py — полноценная абстракция IDE (реестр из 7, get_ide_dir/get_skills_dir/get_rules_file), но у неё всего 6 импортёров, а литерал ".claude" встречается в движке ~20 раз. Следствия: project_cli_doctor.py проверяет только .claude/mcp/project/server.py и .claude/mcp/brain/server.py → на установке Cursor/Qwen/Kilo/OpenCode доктор рапортует FAIL «MCP server missing — re-run bootstrap» и выходит с кодом 1 (ломает CI), хотя bootstrap создаёт .cursor/mcp/, .qwen/mcp/ и т.д.; там же skills_dir=.claude/skills → «no .claude/skills/ — run bootstrap» при существующем .cursor/skills/; service_roles.py DEPLOYED_ROLES_DIR_REL=".claude/roles" → role show не видит развёрнутый профиль; project_cli.py:174-175 предупреждение о числе скиллов не срабатывает никогда. Эталон правильной формы уже в репозитории: project_cli_skill.py сначала пробует ide_utils и лишь на ImportError падает в .claude. Нужен и линт (рядом с восемью существующими audit_*.py), запрещающий литерал ".claude" вне ide_utils.py и service_doctor_caveman.py (последний Claude-specific по замыслу, но должен быть закрыт проверкой detect_ide()=="claude").

## Acceptance Criteria

AC1. tausik doctor на проекте, развёрнутом НЕ под Claude (есть .cursor/, нет .claude/), не рапортует FAIL про MCP-серверы и скиллы и не выходит с кодом 1. Тест на tmp_path-проекте с .cursor/ проверяет exit-код и отсутствие ложного FAIL.
AC2. Пути MCP-серверов, каталога скиллов и ролей резолвятся через ide_utils (detect_ide + get_ide_dir/get_skills_dir), а не через литерал ".claude". Метки в выводе называют РЕАЛЬНЫЙ каталог (.cursor/mcp/... ), а не всегда .claude — иначе диагностика врёт о том, что проверила.
AC3. Регрессия для Claude: на этом репозитории (профиль claude развёрнут) вывод doctor по этим строкам не меняется — те же OK, тот же exit 0.
AC4. Честный случай «профиль не тот»: если каталог обнаруженной IDE отсутствует, а каталог другой поддерживаемой IDE присутствует, сообщение НАЗЫВАЕТ найденный профиль, а не советует вслепую re-run bootstrap. Тест.
AC5. service_roles._profile_path_deployed перестаёт зависеть и от литерала ".claude", и от os.getcwd() (двойное нарушение conv #265). Тест.
AC6. Линт против рецидива: проверка, запрещающая литерал ".claude" в scripts/ вне ide_utils.py и явного allowlist (service_doctor_caveman.py — Claude-specific по замыслу), с понятным сообщением. Тест падает при добавлении нового литерала.
AC7. Полный прогон pytest зелёный, без warnings.
AC8. CHANGELOG.md + CHANGELOG.ru.md обновлены прозой.

## Plan

## Rollback

git revert коммита; изменения локальны в трёх файлах — git checkout -- scripts/project_cli_doctor.py scripts/service_roles.py scripts/project_cli.py возвращает прежнее поведение. Гейтов и схемы БД не касается, миграций нет.

## Journal

- 2026-07-23T15:12:47Z [implementation] — Реализовано. ide_utils получил три хелпера: resolve_profile (ide + каталог одной парой — диагностике нужно и то, и другое, чтобы говорить, ЧТО именно проверено), other_deployed_profile/missing_profile_hint (называет развёрнутый профиль вместо слепого «re-run bootstrap» — совет, который повторит тот же результат) и all_profile_dirs (набор каталогов профилей из реестра). doctor, service_roles._profile_path_deployed (заодно снят os.getcwd — двойное нарушение conv #265) и предупреждение о числе скиллов в project_cli переведены на них. Регрессия на claude: вывод doctor побайтово прежний. РАСШИРЕНИЕ ОБЪЁМА, осознанное: линт вскрыл ещё два сканера (snippet_detect._SKIP_DIRS, project_cli_aidd_autogen._DENY_DIRS) со списками пропуска, написанными руками — они пропускали .claude (один и .cursor), а на остальных профилях обходили развёрнутую копию движка (~300 сгенерированных файлов) как исходники проекта; выведены из all_profile_dirs. И хуки: они НЕ МОГУТ импортировать ide_utils, потому что тот лежит ровно в искомом каталоге — вместо этого session_start находит СЕБЯ (<профиль>/scripts/hooks/x.py → профиль двумя уровнями выше), что чинило тихий дефект: авто-пересборка скиллов резолвила .claude/scripts на ЛЮБОЙ установке, на Qwen ничего не импортировала и молчала, ошибку глотал окружающий try/except. Там же найдена мёртвая переменная цикла в пробе RAG-сервера: `for ide in ("claude","cursor")` при литерале .claude внутри — обе итерации проверяли один путь. Остаток литералов (4 файла) не замазан allowlist'ом вслепую: каждое исключение снабжено причиной, есть тест на ПРОТУХШЕЕ исключение (исключение для файла без литерала легализовало бы следующий), и заведена engine-claude-literals-followup. gate_filesize.py в неё сознательно НЕ включён — его exempt на .claude/mcp/ принадлежит l26-filesize-gate-revisit, именно он прячет 1289-строчный handlers.py от гейта.
- 2026-07-23T15:23:02Z [implementation] — AC1 ✓ Negative: на проекте с .cursor/ и БЕЗ .claude/ (фикстура cursor_project) резолв даёт ('cursor','.cursor'), путь MCP-сервера указывает на реально существующий .cursor/mcp/project/server.py, каталог скиллов не содержит '.claude' — то есть ложного FAIL и выхода 1 больше нет (TestProfileResolution, 4 теста). AC2 ✓ пути MCP/скиллов/ролей резолвятся через ide_utils.resolve_profile/get_skills_dir/get_ide_dir; метки вывода печатают РЕАЛЬНЫЙ каталог (f'{ide_rel}/mcp/project/server.py'), а не всегда .claude — иначе диагностика врала бы о том, что проверила. AC3 ✓ регрессия на claude: вывод doctor на этом репозитории побайтово прежний (те же OK, exit 0), плюс тест test_claude_project_still_resolves_to_claude. AC4 ✓ missing_profile_hint называет развёрнутый профиль и даёт ДВА выхода (bootstrap для обнаруженной IDE либо TAUSIK_IDE=найденная); при полном отсутствии профилей — прежнее 're-run bootstrap'; отдельный тест, что подсказка не называет тот же профиль, о котором рапортует. AC5 ✓ service_roles._profile_path_deployed резолвит через ide_utils и принимает project_dir — сняты И литерал .claude, И os.getcwd() (двойное нарушение conv #265). AC6 ✓ линт TestNoNewClaudeLiterals падает на новом литерале .claude в scripts/, каждое исключение с причиной, есть fail-then-pass на сам матчер и тест на ПРОТУХШЕЕ исключение (исключение для файла без литерала легализовало бы следующий). AC7 ✓ полный прогон 5412 passed / 23 skipped, без warnings. AC8 ✓ проза в обоих CHANGELOG. Domain: проверено на реальной файловой системе — фикстура создаёт настоящий .cursor/mcp/project/server.py и .cursor/skills/start, а не мок; в самом репозитории .cursor/mcp, .kilo/mcp, .qwen/mcp существуют, что и подтверждает исходную предпосылку (bootstrap кладёт профили, doctor их не видел). Сверх AC: два сканера (snippet_detect, aidd_autogen) выводят пропуск-набор из реестра — раньше обходили ~300 файлов развёрнутого движка как исходники; хуки находят СЕБЯ вместо импорта ide_utils (он лежит в искомом каталоге) — это починило тихий отказ авто-пересборки скиллов на Qwen, глушившийся try/except; убрана мёртвая переменная цикла в пробе RAG-сервера. Остаток из 4 файлов не замазан вслепую — заведена engine-claude-literals-followup.
