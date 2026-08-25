---
slug: firewall-blocked-patterns-substring-fp
title: "BLOCKED_PATTERNS сравниваются подстрокой: `rm -rf .venv` и `rm -rf /tmp/x` блокируются как удаление корня"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/hooks/bash_firewall.py (BLOCKED_PATTERNS и место их применения в main), tests/test_hooks.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "WARN_PATTERNS_RE и _git_subcmd_re (закрыто соседней задачей), _scan_target (закрыто задачей про вложенные обёртки), другие хуки"
relevant_files:
  - "scripts/hooks/bash_firewall.py"
  - "tests/test_hooks.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-24T08:36:28Z"
---

## Goal

Найдено эмпирически в сессии #133. BLOCKED_PATTERNS в scripts/hooks/bash_firewall.py матчатся как `pattern.lower() in cmd_lower` — БЕЗ границы слова. Поэтому паттерн "rm -rf ." ловит `rm -rf .venv`, `rm -rf .pytest_cache`, `rm -rf .mypy_cache`, `rm -rf .tausik/tmp`, `rm -rf ./build`, а паттерн "rm -rf /" ловит `rm -rf /tmp/scratch`, `rm -rf /var/tmp/x` — то есть любое удаление по абсолютному пути. Это не гипотеза: firewall ДВАЖДЫ за сессию #133 заблокировал расследование этой же дыры, ровно повторив инцидент от 2026-07-18, который описан в комментарии к самому BLOCKED_PATTERNS (тогда — на DROP TABLE). У блокировки нет approval-пути (сообщение хука честно об этом говорит), единственный выход — TAUSIK_SKIP_HOOKS, то есть каждый false-positive ТРЕНИРУЕТ обход надзора. Цена ошибки здесь асимметрична и уже реализовалась.

## Acceptance Criteria

1. ОБА направления измерены эмпирически на неисправленном коде и записаны в журнал. Направление FP: `rm -rf .venv`, `rm -rf .pytest_cache`, `rm -rf .mypy_cache`, `rm -rf .tausik/tmp`, `rm -rf ./build`, `rm -rf /tmp/scratch`, `rm -rf /var/tmp/x`, `rm -rf /home/u/proj/build` → должны быть rc=0, зафиксировано фактическое. Направление пропуска: варианты написания флагов с той же семантикой (`rm -fr /`, `rm -r -f /`, `rm -f -r /`, `rm -rvf /`, `rm --recursive --force /`) → должны быть rc=2, зафиксировано фактическое.
2. Паттерны rm перестают быть подстроками и начинают описывать КОМАНДУ: удаление корня/текущего каталога блокируется независимо от порядка и написания флагов, а удаление именованного пути (в т.ч. начинающегося с точки или слэша) не блокируется. Остальные BLOCKED_PATTERNS (DROP TABLE, mkfs., dd if=/dev/zero, > /dev/sda, fork bomb) остаются подстроками осознанно — для них подстрока и есть верная семантика; решение зафиксировано комментарием в коде, а не молча.
3. Тесты: каждый FP из AC-1 закреплён негативом, каждый вариант флагов — позитивом. Негативы подтверждённо падают ДО фикса (у них rc=2), позитивы-варианты подтверждённо падают ДО фикса (у них rc=0) — факт падения проверен прогоном.
4. Сохранены прежние позитивы: `rm -rf /`, `rm -rf /*`, `rm -rf .`, `rm -rf "/"`, `rm -rf "."`, а также формы за префиксом и обёрткой (`sudo rm -fr /`, `bash -c 'rm -fr /'`).
5. pytest tests/test_hooks.py зелёный, verify --task с ИСПОЛНЕННЫМ pytest, CHANGELOG.md + CHANGELOG.ru.md, bootstrap --ide all для профилей.

## Plan

## Rollback

git revert коммита задачи + bootstrap.py --ide all. Риск отката асимметричен и учтён: откат ВОЗВРАЩАЕТ ложные блокировки, но не открывает дыру, поэтому откат безопасен для надзора. Если новая форма паттернов даст пропуск — это блокирующий регресс, и правильный ход не откат, а немедленный дофикс с добавлением позитива в тесты.

## Journal

- 2026-07-24T08:36:26Z [implementation] — AC-1: ✓ измерено на НЕИСПРАВЛЕННОМ коде — 9 false-positive (rm -rf .venv/.pytest_cache/.mypy_cache/.tausik~tmp/./build//tmp/scratch//var/tmp/x/.git~hooks~tmp//home/u/proj/build → rc=2) и 7 пропусков (rm -fr /, rm -r -f /, rm -f -r /, rm -rvf /, rm --recursive --force /, sudo rm -fr /, обёртка → rc=0). Паттерн ошибался в ОБЕ стороны одновременно. AC-2: ✓ введён _rm_wipes_a_root — флаги читаются как флаги (любой порядок, слитно/раздельно, короткие/длинные), операнды как операнды, требуются ОБА -r и -f; остальные BLOCKED_PATTERNS оставлены подстроками с комментарием ПОЧЕМУ (их смысл не зависит от написания команды). AC-3: ✓ tested via tests/test_hooks.py — 6 негативов и 8 позитивов-вариантов, все подтверждённо давали неверный rc до фикса. AC-4: ✓ прежние позитивы сохранены, включая rm -rf "/" и rm -rf "." (существующие кейсы quoted_slash_arg_still_blocked / quoted_dot_arg_still_blocked зелёные), плюс новый негатив rm -f /→0 (без -r пара необратимости не собрана). AC-5: ✓ pytest tests/test_hooks.py 102 passed; verify #1250 pytest ИСПОЛНЕН 7125 ms; CHANGELOG.md + CHANGELOG.ru.md; bootstrap --ide all выполнен. Domain: результат осмыслен вне тестов — rm(1) не различает порядок флагов и допускает кластеры, поэтому детектор, перечисляющий написания, семантически неверен по определению; проверено на реальных путях повседневных чисток (.venv, .pytest_cache, node_modules, /tmp) и на реальных написаниях wipe-команды. Остаток (~, .., *, $HOME) не замолчан: записан в docstring и заведён задачей firewall-rm-wipe-targets-policy.
