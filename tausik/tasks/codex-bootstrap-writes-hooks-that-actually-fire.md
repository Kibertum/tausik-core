---
slug: codex-bootstrap-writes-hooks-that-actually-fire
title: "Codex получает bootstrap с ЖИВЫМИ хуками: у хоста есть API, а лежащий в проекте файл раскрывается в несуществующие пути"
status: done
epic: release-19-renar-conformance
story: codex-first-class-19
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "Не трогать .claude/ и другие развёрнутые профили руками — они пересоздаются bootstrap-ом; не менять набор хуков, только способ построения пути"
relevant_files:
  - "bootstrap/bootstrap_codex.py"
  - "bootstrap/bootstrap_codex_mcp.py"
  - "bootstrap/bootstrap_config.py"
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_hooks.py"
  - "tests/test_bootstrap_codex.py"
  - "tests/test_ide_single_source.py"
  - "docs/ru/model-providers.md"
  - "docs/en/model-providers.md"
  - "scripts/enforcement_coverage.py"
  - "tests/test_enforcement_coverage.py"
scope_paths:
  - "bootstrap/bootstrap_codex.py"
  - "bootstrap/bootstrap_codex_mcp.py"
  - "bootstrap/bootstrap_config.py"
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_hooks.py"
  - "tests/test_bootstrap_codex.py"
  - "tests/test_ide_single_source.py"
  - "docs/ru/model-providers.md"
  - "docs/en/model-providers.md"
  - "scripts/enforcement_coverage.py"
  - "tests/test_enforcement_coverage.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-09T16:23:27Z"
---

## Goal

ЗАМЕР, смена #241, сделан на самом бинаре Codex (codex.exe), а не по документации. Codex ИМЕЕТ полноценный API хуков: в бинаре присутствуют строки hooks.json, .codex/hooks, PreToolUse, PostToolUse, SessionStart, UserPromptSubmit, а также hook_event_name, hookSpecificOutput и permissionDecision - то есть тот же протокол обмена, что у Claude Code. Предпосылка тикета GitLab #17 о том, что Rule 1 нельзя сделать жёстким до появления у Codex эквивалентного API, УСТАРЕЛА: API есть, и Rule 1 под Codex может и обязан быть жёстким хуком, а не инструкцией.

ОДНОВРЕМЕННО НАЙДЕН ЖИВОЙ ДЕФЕКТ. В этом проекте уже лежит .codex/hooks.json (не наш - bootstrap его не создаёт, codex отсутствует в SCAFFOLD_IDES). В нём тринадцать хуков, и КАЖДАЯ команда имеет вид: python -X utf8 ${CLAUDE_PROJECT_DIR}/.claude/scripts/hooks/<имя>.py. Строки CLAUDE_PROJECT_DIR в бинаре Codex НЕТ - проверено тем же способом, что и наличие остальных. Переменная раскроется в пустоту, путь станет /.claude/scripts/hooks/task_gate.py и не найдётся. Следствие: под Codex прямо сейчас молча не работает НИ ОДИН гейт - ни Rule 1, ни ACL области, ни firewall, ни сканер секретов - при том что файл на диске выглядит подключённым. Это ровно тот класс, ради которого в проекте заведён gate_outcome.could_not_run: механизм, объявляющий себя работающим и не работающий.

ЧТО ДЕЛАЕТСЯ. Генератор пишет .codex/hooks.json с АБСОЛЮТНЫМИ путями - тем же решением, что принято для OpenCode (gotcha #201: хост не раскрывает переменных рабочей области). Набор хуков берётся из ОДНОГО источника вместе с claude-профилем, чтобы два хоста не разошлись молча.

## Acceptance Criteria

AC-1 bootstrap.py --ide codex принимается парсером и входит в --ide all; SCAFFOLD_IDES пополнен, и членство подкреплено генератором, а не только строкой в списке. AC-2 Чистый проект после --ide codex получает .codex/hooks.json, где КАЖДАЯ команда - существующий абсолютный путь: проверяется тем, что os.path.isfile истинен для каждого пути в файле. AC-3 НЕГАТИВ, главный: в сгенерированном файле НЕТ ни одной нераскрываемой переменной - ни ${CLAUDE_PROJECT_DIR}, ни любой другой формы ${...} внутри command. Тест ловит именно это, потому что именно это сделало существующий файл мёртвым. AC-4 Повторный прогон не растит и не дублирует хуки и сохраняет чужие записи пользователя: идемпотентность проверяется двумя прогонами подряд и сравнением. AC-5 Набор хуков Codex и Claude происходит из одного объявления - тест краснеет, если в claude-профиле появился хук, которого нет у codex.

## Plan

## Rollback

Новый генератор и строка в SCAFFOLD_IDES; откат - git revert. Существующие профили не трогаются: генератор пишет только .codex/, который в .gitignore и воссоздаётся bootstrap-ом.

## Journal

- 2026-09-09T16:06:49Z [implementation] — ЗАМЕР ПОДТВЕРЖДЁН НА БИНАРЕ codex.exe: есть hooks.json, .codex/hooks, .codex/config.toml, .codex/skills, .codex/agents, AGENTS.md, SKILL.md, а из событий — PreToolUse, PostToolUse, SessionStart, SessionEnd, UserPromptSubmit, Stop, PreCompact, Notification, SubagentStop. Протокол тот же: hook_event_name, hookSpecificOutput, permissionDecision.
- 2026-09-09T16:06:51Z [implementation] — ОТСУТСТВУЮТ в бинаре: CLAUDE_PROJECT_DIR, CODEX_PROJECT_ROOT, workspaceFolder, CODEX_WORKSPACE. Переменной рабочей области у Codex НЕТ ни одной — отсюда абсолютные пути, как у OpenCode (gotcha #201).
- 2026-09-09T16:06:52Z [implementation] — ЗАМЕР ДО/ПОСЛЕ на живом профиле: в лежавшем .codex/hooks.json было 24 вхождения CLAUDE_PROJECT_DIR. После bootstrap --ide codex — 0 подстановок из 24 команд, все пути существуют на диске.
- 2026-09-09T16:06:53Z [implementation] — AC-1: ✓ bootstrap.py --ide codex --dry-run отработал; codex в SCAFFOLD_IDES и в --ide all. tests/test_bootstrap_codex.py::TestCodexЭтоЦельПервогоКласса::test_членство_подкреплено_генератором
- 2026-09-09T16:06:54Z [implementation] — AC-2: ✓ tests/test_bootstrap_codex.py::TestКаждыйПутьСуществует::test_интерпретатор_и_скрипт_на_месте
- 2026-09-09T16:06:54Z [implementation] — AC-3: ✓ tests/test_bootstrap_codex.py::TestНиОднойНераскрываемойПеременной::test_в_живом_профиле_нет_подстановок и test_проверка_поймала_бы_сломанный_файл
- 2026-09-09T16:06:55Z [implementation] — AC-4: ✓ tests/test_bootstrap_codex.py::TestПовторныйПрогонИЧужиеКлючи::test_два_прогона_дают_один_файл и test_чужие_ключи_переживают_перезапись
- 2026-09-09T16:06:56Z [implementation] — AC-5: ✓ tests/test_bootstrap_codex.py::TestНаборОдинНаДваХоста::test_codex_повторяет_набор_claude_событие_в_событие
- 2026-09-09T16:06:57Z [implementation] — Domain: 24 команды содержат абсолютный путь к интерпретатору венва проекта и к скрипту в .codex/scripts/hooks — обе стороны проверены os.path.isfile на живом дереве, то есть хук запустится тем же питоном, что и весь остальной инструмент.
- 2026-09-09T16:06:59Z [implementation] — ЗАМЕЧЕНО ПОПУТНО, НЕ ЧИНИТСЯ ЗДЕСЬ: bootstrap_qwen.py дублирует набор хуков собственным списком вместо build_hooks_dict. Это тот же класс расхождения, против которого написан AC-5, но у другого хоста и вне области этой задачи.
- 2026-09-09T16:13:02Z [implementation] — ДВЕ ОХРАНЫ ЗАКРЕПЛЯЛИ ПРЕЖНЮЮ ПРАВДУ и покраснели правильно: test_ide_single_source::test_windsurf_codex_discoverable_but_not_scaffolded утверждал, что codex НЕ scaffolded, а таблица платформ в docs/{ru,en}/model-providers.md говорила 'нет'. Обе обновлены: windsurf остаётся неразвёрнутым, codex переехал в отдельный тест scaffold-capable, таблица называет ФАКТИЧЕСКИЕ артефакты (.codex/hooks.json, .codex/skills/, AGENTS.md), а проза называет и цену абсолютных путей.
- 2026-09-09T16:13:02Z [implementation] — ПОПУТНО ИЗМЕРЕНО: навыки в .codex/skills/ раскладываются ОБЩИМ шагом копирования, а не отдельным генератором — их 14 и каждый несёт SKILL.md. Задача codex-gets-the-skills-the-host-already-reads сокращается: строить нечего, надо проверить IDE-оверлей и закрепить тестом.
- 2026-09-09T16:22:02Z [implementation] — ЕЩЁ ОДНА СЛЕПОТА, НАЙДЕННАЯ ДОГФУДИНГОМ: doctor писал 'codex: none' про принуждение, при том что в .codex/ лежали 24 команды хуков. Причина — SETTINGS_FILES в enforcement_coverage.py знал только settings.json, а Codex держит тот же груз в hooks.json. Отчёт О ПРИНУЖДЕНИИ недосчитывал принуждения, то есть говорил читателю обратное правде. Форма имени добавлена в объявленный список (комментарий рядом прямо называет записи ФОРМОЙ артефакта, а не хостом), закреплено tests/test_enforcement_coverage.py::TestCodexПлатитЗаСВОЁИмяФайла. После развёртывания doctor показывает 'codex: 24 hook commands'.
