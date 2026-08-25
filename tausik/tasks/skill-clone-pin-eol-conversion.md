---
slug: skill-clone-pin-eol-conversion
title: "CRLF: ядро клонирует вендор-репу с core.autocrlf потребителя — подпись платформозависима"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/skill_manager.py (clone_repo), tests/test_skill_manager.py. Зеркала через bootstrap."
scope_exclude: "Не менять supply_sign.py: подпись остаётся подписью сырых байт (решение #129)."
relevant_files:
  - "scripts/skill_manager.py"
  - "scripts/skill_git.py"
  - "tests/test_skill_manager.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T12:59:02Z"
---

## Goal

Сделать вендор-клон байт-в-байт равным объектам репозитория, независимо от git-конфига пользователя. clone_repo (scripts/skill_manager.py:122) зовёт 'git clone --depth 1' и наследует core.autocrlf. Репро: скилл, подписанный по LF, в клоне с autocrlf=true даёт другой sha256 и другой size -> 'Install refused — modified: SKILL.md'; с autocrlf=false проходит. Правка: 'git -c core.autocrlf=false -c core.eol=lf clone ...', затем 'git config core.autocrlf false' в клоне (иначе последующий git pull --ff-only снова наследует глобальный конфиг). Учесть уже существующие вендор-клоны: их надо инвалидировать или перечекаутить, иначе они остаются с CRLF.

## Acceptance Criteria

1) clone_repo клонирует с принудительно отключённой конверсией: git -c core.autocrlf=false -c core.eol=lf clone. 2) В самом клоне ставится core.autocrlf=false, иначе последующий git pull --ff-only снова унаследует глобальный конфиг. 3) Тест: репозиторий с LF-байтами, подписанный манифест, клон при глобальном autocrlf=true — sha256 совпадает. 4) Существующие вендор-клоны, сделанные до правки, не остаются молча сломанными. Негативные сценарии: 5) Ошибка, если клон при core.autocrlf=true даёт другой sha256 — это ровно тот баг. 6) Ошибка, если git pull в уже склонированной репе конвертирует окончания строк. 7) Ошибка, если полный прогон даёт новое падение.

## Plan

## Rollback

git checkout -- scripts/skill_manager.py tests/test_skill_manager.py; bootstrap для зеркал.

## Journal

- 2026-07-10T12:57:54Z [implementation] — AC verified: 1. ✓ clone_repo зовёт git с _EOL_PINS ('-c core.autocrlf=false -c core.eol=lf'). 2. ✓ _pin_eol_config пишет пин в локальный конфиг клона — TestCloneEolPinning::test_pin_is_persisted_into_the_clone. Необходимость доказана экспериментом: клон с одним только -c, затем 'git pull --ff-only' при GLOBAL autocrlf=true -> MISMATCH; с локальным пином -> OK. 3. ✓ test_clone_reproduces_publisher_bytes_under_hostile_global_config: sha совпадает с издательским при GIT_CONFIG_GLOBAL c autocrlf=true. 4. ✓ Устаревшие клоны не остаются молча сломанными — _eol_is_pinned=False приводит к пересозданию (test_stale_unpinned_cache_is_recloned, печатает 'Re-cloning'). 5. ✓ (негативный) Клон без пинов при autocrlf=true даёт другой sha — воспроизведено в scratchpad/pull_eol.py. 6. ✓ (негативный) test_pull_does_not_reconvert. 7. ✓ (негативный) test_existing_unpinned_repo_is_recloned_not_pulled. Побочная находка: старый TestCloneRepo::test_existing_repo_pulls проходил СЛУЧАЙНО. Он утверждал any('pull' in str(cmd)), а pytest кладёт tmp_path в каталог с именем теста — 'test_existing_repo_pulls0'. Подстрока 'pull' находилась в пути репозитория, а не в команде, поэтому тест был зелёным при любой git-подкоманде. После правки он реально шёл по ветке пересоздания и всё равно был зелёным. Переписан на проверку argv[1]. Domain: живой прогон scratchpad/clone_pin_live.py при GIT_CONFIG_GLOBAL с autocrlf=true — clone_repo даёт sha 6f55316751d99a64 (совпадает с издательским), пин выставлен, pull не конвертирует, снятие пина приводит к пересозданию и восстановлению пина. rmtree_force при этом реально снёс read-only git-паки на Windows.
