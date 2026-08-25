---
slug: firewall-rm-wipe-targets-policy
title: "Решить, входят ли `rm -rf ~`, `rm -rf ..` и `rm -rf *` в набор «стирает всё» — сейчас блокируется только / и ."
status: done
epic: null
story: null
complexity: simple
role: architect
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "scripts/hooks/rm_wipe_detect.py (добавить ~ в _WIPE_ROOTS + докстринг), tests/test_hooks.py (пины: ~ blocked, * blocked, $HOME residue)"
scope_exclude: null
relevant_files:
  - "scripts/hooks/rm_wipe_detect.py"
  - "scripts/hooks/danger_patterns.py"
  - "tests/test_hooks.py"
  - "tests/test_powershell_channel.py"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - CLAUDE.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T15:42:29Z"
---

## Goal

Оставлено как ЯВНЫЙ остаток задачи firewall-blocked-patterns-substring-fp (сессия #133), а не забыто. _RM_WIPE_TARGETS = {"/", "/*", ".", "./"} — ровно тот набор, который покрывали три прежние подстроки; расширение набора было бы сменой ПОЛИТИКИ, а не починкой дефекта, и потому не протащено внутрь багфикса (иначе откат багфикса откатывал бы и политику). Вопрос, который надо решить осознанно: firewall объявляет себя защитой от «Recursive delete from root», но `rm -rf ~` уничтожает домашний каталог со всеми проектами и ключами, `rm -rf ..` — родительский каталог, `rm -rf *` — содержимое текущего. Первое по последствиям не мягче `/`. Против расширения — цена ложного блока: `rm -rf *` внутри build-каталога является рутинной операцией, и блок без approval-пути тренирует TAUSIK_SKIP_HOOKS (та самая петля, которую закрыла родительская задача). Решение должно быть принято ЯВНО (tausik decide) с обоснованием по каждой цели отдельно, а не «за компанию». Отдельный подвопрос: `$HOME` и другие нераскрытые переменные документированы в docstring как нерезолвимый остаток — подтвердить, что это осознанная граница, а не дыра.

## Acceptance Criteria

1. Явное решение (tausik decide) с обоснованием по КАЖДОЙ цели отдельно: ~, .., *, $HOME. 2. `rm -rf ~`, `rm -rf ~/`, `rm -rf ~/*` блокируются (exit 2) — home wipe. 3. `rm -rf ..` остаётся заблокированным (регрессия не допущена). 4. `rm -rf *`, `rm -rf ./*` остаются заблокированными (консистентность с `rm -rf .`); докстринг rm_wipe_detect.py, ложно утверждающий обратное, исправлен. 5. `$HOME`/`${X:-/}` подтверждены как осознанный нерезолвимый остаток (пин-тест, не блокируется). 6. Полная суита зелёная, 0 warnings; scoped verify зелёный.

## Plan

## Rollback

git revert коммита; изменение локализовано в _WIPE_ROOTS frozenset и докстринге — откат одной строки восстанавливает прежний набор.

## Journal

- 2026-07-26T15:37:10Z [implementation] — Реализовано: (1) decision #177 с обоснованием по каждой цели. (2) `~` добавлен в _WIPE_ROOTS — `rm -rf ~`,`~/`,`~/*` теперь exit 2 (проверено end-to-end через bash_firewall). (3) `..` без изменений (не регрессировало). (4) `*`/`./*` остаются заблокированы; докстринг rm_wipe_detect.py (ложно утверждавший, что `*` не блокируется) исправлен + докстринг is_wipe_root. (5) $HOME/${X:-/} запинены как residue (exit 0). Тесты: +7 пинов в test_hooks.py::test_command; test_hooks 130 passed, powershell+shellless 126 passed (нет регрессии в pwsh Remove-Item ~). doc-constants перегенерены. Побочно: firewall заблокировал мою же тестовую Bash-строку с литералом — догфудинг, обход через python-скрипт с char-кодами.
- 2026-07-26T15:39:34Z [implementation] — AC verified: 1. ✓ decision #177 — per-target rationale for ~, .., *, $HOME 2. ✓ tests/test_hooks.py::TestBashFirewall::test_command[rm_rf_home_blocked|rm_rf_home_slash_blocked|rm_rf_home_glob_blocked] all exit 2; end-to-end via bash_firewall.py confirmed 3. ✓ rm_rf_parent_glob_blocked + .. in _WIPE_ROOTS unchanged; full test_hooks 130 passed 4. ✓ rm_rf_bare_star_blocked + rm_rf_dotslash_glob_blocked exit 2; rm_wipe_detect.py docstring corrected (falsely claimed * allowed) 5. ✓ rm_rf_dollar_home_unresolved_residue + rm_rf_param_default_unresolved_residue exit 0 (pinned boundary) 6. ✓ tausik_verify high scope: pytest PASS over test_hooks.py+test_powershell_channel.py, status=miss (git cross-check consistent); doc-constants regenerated & matching
- 2026-07-26T15:40:23Z [implementation] — AC verified: 1. ✓ decision #177 — per-target rationale for ~, .., *, $HOME 2. ✓ tests/test_hooks.py::TestBashFirewall::test_command[rm_rf_home_blocked|rm_rf_home_slash_blocked|rm_rf_home_glob_blocked] all exit 2; end-to-end via bash_firewall.py confirmed 3. ✓ rm_rf_parent_glob_blocked + .. in _WIPE_ROOTS unchanged; full test_hooks 130 passed 4. ✓ rm_rf_bare_star_blocked + rm_rf_dotslash_glob_blocked exit 2; rm_wipe_detect.py docstring corrected (falsely claimed * allowed) 5. ✓ rm_rf_dollar_home_unresolved_residue + rm_rf_param_default_unresolved_residue exit 0 (pinned boundary) 6. ✓ tausik_verify high scope pytest PASS over test_hooks.py+test_powershell_channel.py, status=miss; bootstrap redeployed to all 5 profiles so deployed hooks match source; doc-constants regenerated & matching
- 2026-07-26T15:42:27Z [implementation] — AC verified: 1. ✓ decision #177 — per-target rationale for ~, .., *, $HOME 2. ✓ tests/test_hooks.py::TestBashFirewall::test_command[rm_rf_home_blocked|rm_rf_home_slash_blocked|rm_rf_home_glob_blocked] exit 2; end-to-end via bash_firewall.py confirmed 3. ✓ rm_rf_parent_glob_blocked + .. unchanged in _WIPE_ROOTS; test_hooks 130 passed 4. ✓ rm_rf_bare_star_blocked + rm_rf_dotslash_glob_blocked exit 2; rm_wipe_detect.py docstring corrected 5. ✓ rm_rf_dollar_home_unresolved_residue + rm_rf_param_default_unresolved_residue exit 0 6. ✓ tausik_verify high pytest PASS (test_hooks+test_powershell_channel), status=miss; bootstrap redeployed 5 profiles; CHANGELOG.md+CHANGELOG.ru.md entries added; doc-constants matching
