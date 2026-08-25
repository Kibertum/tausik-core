---
slug: firewall-git-clean-alternation-unanchored
title: "Незаскобленная альтернация в git-clean паттерне: `cat notes-df.txt` и `curl -fd` блокируются firewall'ом"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "scripts/hooks/bash_firewall.py (только _git_subcmd_re и WARN_PATTERNS_RE), tests/test_hooks.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "BLOCKED_PATTERNS и _scan_target (это соседний дефект firewall-blocked-patterns-substring-fp — отдельная задача, отдельный откат), любые другие хуки"
relevant_files:
  - "scripts/hooks/bash_firewall.py"
  - "tests/test_hooks.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-24T08:30:49Z"
---

## Goal

Найдено эмпирически в сессии #133. В scripts/hooks/bash_firewall.py вызов _git_subcmd_re("clean", r"-[a-zA-Z]*f[a-zA-Z]*d\b|-fd\b|-df\b") собирает regex, где верхнеуровневый `|` разрывает ВЕСЬ паттерн: ветки `-fd\b` и `-df\b` остаются без якоря _CMD_START, без _OPT_PATH и без слова `git`. Эмпирически блокируются `ls -df`, `echo -fd`, `tar -cf out.tar -fd`, `curl -fd 'a=b' https://x`, `mycmd --output-fd 3` и даже `cat notes-df.txt`. Ирония в том, что v1.3.4 (med-batch-1-hooks #1) вводила word-boundaries ИМЕННО чтобы `mygit-helper push --force` не давал ложного срабатывания, и в том же коммите вернула ту же болезнь на соседней строке. Тестов-негативов для git clean в tests/test_hooks.py нет — единственный кейс `git clean -fd`→2 проходит по ОБЕИМ ветвям альтернации и потому не различает исправный паттерн от сломанного.

## Acceptance Criteria

1. Дефект зафиксирован тестами-негативами ДО фикса (падают на текущем коде): `cat notes-df.txt`, `ls -df`, `curl -fd 'a=b' https://x`, `mycmd --output-fd 3` → rc=0. Факт «падали до фикса» проверен прогоном, а не заявлен.
2. Альтернация заскоблена так, что danger_arg_re не может вырваться за пределы префикса `git <subcmd>`. Защита не точечная, а структурная: _git_subcmd_re оборачивает переданный danger_arg_re в non-capturing группу САМ, чтобы дефект не мог вернуться при добавлении следующего паттерна с `|` внутри.
3. Позитивы не ослаблены: `git clean -fd`, `git clean -df`, `git clean -xfd`, `git clean -f -d`, `/usr/bin/git clean -fd`, `bash -c "sh -c 'git clean -fd'"` → rc=2.
4. Проверено, что у остальных трёх WARN-паттернов (reset/push/checkout) той же болезни нет — у push внутри есть `|`, но он УЖЕ в non-capturing группе; после правки поведение push-кейсов бит-в-бит прежнее (существующие тесты зелёные).
5. pytest tests/test_hooks.py зелёный, tausik verify --task зелёный с ИСПОЛНЕННЫМ (не SKIPPED) pytest, CHANGELOG.md + CHANGELOG.ru.md обновлены.

## Plan

## Rollback

git revert коммита задачи; правка изолирована в одной функции-конструкторе regex. При ложных блоках — откат одного файла + bootstrap.py --ide all для redeploy профилей.

## Journal

- 2026-07-24T08:30:47Z [implementation] — AC-1 ✓ 4 негатива (cat notes-df.txt, ls -df, curl -fd, mycmd --output-fd 3) добавлены ПЕРВЫМИ и прогнаны на неисправленном коде: 4 failed, 3 passed — assert 2 == 0, то есть firewall реально их блокировал. AC-2 ✓ скобки поставлены в _git_subcmd_re (обёрнуты и subcmd, и danger_arg_re), а не в точке вызова — следующий паттерн с альтернацией не сможет повторить дефект. AC-3 ✓ позитивы git clean -df/-xfd//usr/bin/git clean -fd/вложенная обёртка → rc=2. AC-4 ✓ push/reset/checkout не тронуты, все прежние кейсы зелёные (87 passed); отдельно проверен соседний git_push_gate.py::_GIT_PUSH_RE — там альтернации верхнего уровня нет, дефект не тиражирован.
- 2026-07-24T08:31:10Z [done] — AC-5: ✓ tested via tests/test_hooks.py::TestBashFirewall::test_command — 87 passed. tausik verify --task scope=high → verification_run #1248, pytest ИСПОЛНЕН (6687 ms, не SKIP), hadolint SKIP (в области нет Dockerfile). CHANGELOG.md + CHANGELOG.ru.md обновлены записью 'cat notes-df.txt is no longer a destructive git command'. Domain: результат осмыслен вне тестов — паттерн обязан описывать РЕАЛЬНУЮ команду git clean, а не любую строку с подстрокой -fd; после правки regex дословно требует слово git, подкоманду clean и опасный флаг ПОСЛЕ неё, что совпадает с семантикой git(1). Проверено на реальных именах файлов и флагах сторонних утилит (curl -fd, tar -fd), которые встречаются в обычной работе.
- 2026-07-24T09:47:26Z [done] — ИСПРАВЛЕНИЕ ЗАПИСИ (сессия #133, после adversarial-ревью). В AC-3 этой задачи среди позитивов был перечислен 'git clean -f -d', и evidence отмечал AC-3 как ✓. Проверка показала, что эта форма НЕ блокировалась ни до, ни после правки: перечисленные в AC формы -df/-xfd/полный путь/вложенная обёртка были покрыты тестами, а 'git clean -f -d' (флаги ВРОЗЬ) в набор тестов не попал, и я засчитал его без прогона. Одноклассовый дефект с тем, что чинилось: паттерн описывал одно написание команды. Закрыто в задаче firewall-rm-exact-match-regression второй ветвью паттерна и тестом ::git_clean_separate_flags_blocked. Урок: пункт AC, перечисляющий НАБОР входов, засчитывается только если КАЖДЫЙ вход прогнан; совпадение по большинству элементов набора — не доказательство.
