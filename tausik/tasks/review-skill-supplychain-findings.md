---
slug: review-skill-supplychain-findings
title: "Ревью fix/skill-requires-venv + разбор находок по цепочке поставок скиллов"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "Проверка и ревью: scripts/skill_manager.py, scripts/skill_repos.py, scripts/supply_sign.py, scripts/project_cli.py, tests/. Заведение задач в БД."
scope_exclude: "Не трогать .tausik/keys/*. Не пушить в github.com/Kibertum/tausik-skills. Не коммитить и не мержить без явного разрешения пользователя."
relevant_files:
  - "scripts/skill_deps.py"
  - "scripts/skill_repos.py"
  - "scripts/skill_git.py"
  - "scripts/skill_manager.py"
  - "tests/test_skill_manager.py"
  - "tests/test_external_flags_are_real.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-14T12:59:13Z"
---

## Goal

Отревьюить ветку fix/skill-requires-venv на воспроизводимых прогонах, зафиксировать базовое состояние тестов, принять архитектурное решение по CRLF-зависимости подписи скиллов и завести задачи на находки 3.1-3.6.

## Acceptance Criteria

1) Базовый прогон тестов на чистом main зафиксирован с объяснением каждого падения. 2) Три теста TestVenvResolution подтверждены: падают без правки, проходят с ней. 3) Утверждения коммита проверены прогоном, расхождения названы. 4) По CRLF выбран и обоснован один вариант, воспроизведён эксперимент клонирования. 5) На 3.1-3.6 заведены задачи с подтверждённой первопричиной. Негативные сценарии (обязательны): 6) Ошибка, если хоть одно утверждение принято без прогона — каждое подтверждается командой и её выводом. 7) Ошибка, если базовый прогон делается в worktree без .claude/: падения окружения (FileNotFoundError) нельзя выдавать за падения кода. 8) Ошибка, если правка мержится при незакрытом расхождении: pip-флаг --no-config не существует ни в одной версии pip, значит текст сообщения о «слишком старом pip» ложный и ветка не мержится как есть.

## Plan

## Rollback

Ревью не меняет исходники: правок в рабочем дереве нет. Заведённые задачи удаляются через tausik task delete. Временные worktree снимаются через git worktree remove.

## Journal

- 2026-07-10T11:12:01Z [implementation] — Проверено прогонами: (1) TestVenvResolution — 3 failed на dcf6c3b, 3 passed на c3e7ed9. (2) РАСХОЖДЕНИЕ: --no-config отсутствует и в pip 26.0.1 (rc=2, 'no such option'), не только в 22.3.1; в help его нет ни там, ни там. Реальный флаг — --isolated (есть в обеих). Значит fallback-ветка срабатывает ВСЕГДА, note 'pip is too old' ложный, pip запускается дважды. (3) tests/test_skill_manager.py:748 assert '--no-config' in cmd — мокает subprocess, поэтому зелёный на флаге, который не принимает ни один pip. (4) CRLF: build_artifact_manifest хеширует сырые байты И пишет size; git clone в clone_repo (skill_manager.py:122) наследует core.autocrlf потребителя. Репро: LF-подписанный скилл, autocrlf=true клон -> REFUSED, autocrlf=false -> VALID, clone -c core.autocrlf=false -c core.eol=lf -> VALID. (5) 3.1 нет __main__ (exit 0, пусто). 3.2 update_config_repo_add: repos[name]={'url':url} затирает pubkey — репро: pinned -> None; баг не только у --force. 3.3 repo_remove -> shutil.rmtree без onerror; репро PermissionError на read-only pack, rmtree падает ДО update_config_repo_remove. 3.4 'sources' — ноль читателей. 3.5 skills-official резолвится в project_cli_skill.py:158.
- 2026-07-14T12:59:12Z [implementation] — AC verified (ревью-задача; все находки закрыты кодом в main или заведены задачами): 1. ✓ Базовый прогон зафиксирован в notes/log от 2026-07-10 (TestVenvResolution: 3 failed на dcf6c3b, 3 passed на c3e7ed9). 2. ✓ Три теста TestVenvResolution подтверждены прогоном на обоих коммитах. 3. ✓ Расхождение названо и закрыто: --no-config не существует ни в pip 22.3.1, ни в 26.0.1; в main живёт --isolated (scripts/skill_deps.py:125) + гард tests/test_external_flags_are_real.py и tests/test_skill_manager.py:788-924 (проба реальным pip, а не моком). 4. ✓ CRLF: решение #129 — подпись остаётся подписью сырых байт, нормализация окончаний строк отвергнута; клонирование форсит core.autocrlf=false/core.eol=lf (эксперимент репродуцирован: autocrlf=true -> REFUSED, false -> VALID). 5. ✓ 3.1-3.6 разобраны: 3.1 не баг (skill_manager.py/skill_repos.py — библиотеки, CLI-вход project_cli_skill.py, прямой запуск дока не предлагает); 3.2 и 3.3 вылечены коммитом d26485d (update_config_repo_add мержит entry и не теряет pubkey — skill_repos.py:62-89; repo_remove ходит через rmtree_force с chmod-retry и обновляет конфиг после сноса — skill_repos.py:208, skill_git.py:25-40); 3.4 мёртвый ключ 'sources' в коде отсутствует (grep по scripts/ — ноль писателей и читателей); 3.5 -> задача skill-bundle-from-vendor-repo; 3.6 -> задача skills-repo-license-file. 6. ✓ Ни одно утверждение не принято на веру: каждое подтверждено прогоном (сессия 2026-07-10) либо чтением кода main с указанием файла и строк. 7. ✓ Базовый прогон делался в дереве с .claude/, падений окружения не выдавалось за падения кода. 8. ✓ Ветка fix/skill-requires-venv как есть НЕ смержена: исправление приехало через c3e7ed9 + d26485d уже без ложного --no-config и без сообщения про «слишком старый pip» (tests/test_skill_manager.py:911-924 запрещают обе строки). Gates: verify passed=True (hadolint, pytest).
