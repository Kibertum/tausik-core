---
slug: port-external-pr5-hook-coverage
title: "Перенести внешний PR #5 (покрытие хуков) в основной репозиторий: часть уже сделана в 1.8, часть нет"
status: done
epic: release-19-renar-conformance
story: release19-tracker-promises
complexity: complex
role: backend
stack: null
tier: substantial
call_budget: 90
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/write_tools.py"
  - "scripts/hooks/task_gate.py"
  - "scripts/hooks/scope_write_gate.py"
  - "scripts/hooks/secret_scan.py"
  - "scripts/hooks/memory_pretool_block.py"
  - "scripts/hooks/memory_posttool_audit.py"
  - "scripts/hooks/auto_format.py"
  - "scripts/hooks/shell_channel.py"
  - "scripts/host_mechanisms.py"
  - "scripts/renar_mandatory_clauses.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "tests/test_pr5_hook_coverage.py"
  - "tests/test_bootstrap_hooks_parity.py"
  - "tests/test_memory_pretool_block_hook.py"
  - "tests/test_memory_posttool_audit_hook.py"
  - "tests/test_memory_sinks.py"
  - "docs/en/hooks.md"
  - "docs/ru/hooks.md"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
  - RENAR-CONFORMANCE.yaml
scope_paths:
  - "scripts/hooks/*.py"
  - "bootstrap/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on:
  - pr5-was-promised-a-merge-and-planned-as-a-reimplementation
completed_at: "2026-09-13T17:07:42Z"
---

## Goal

Каждое утверждение PR #5 проверено против дерева 1.8 и либо перенесено с тестом, либо закрыто как уже сделанное — с указанием, ЧЕМ именно.

## Acceptance Criteria

AC-1: the table 'PR #5 claim -> state in 1.8/1.9' stands in the journal (four of six guards closed in 1.8, the fail-secure flip in 1.9). AC-2: ported with tests: one source of tool names and payload path fields (scripts/hooks/write_tools.py: BUILTIN_WRITE_TOOLS, MCP_WRITE_TOOLS from PR #5, PATH_FIELDS file_path/notebook_path/path/relative_path/destination, edited_paths); NotebookEdit and the MCP editors covered by task_gate, scope_write_gate, secret_scan, memory_pretool_block, memory_posttool_audit; MultiEdit in auto_format; mcp__windows-mcp__PowerShell on the shell hooks; bootstrap matchers (Claude, Qwen, Codex via build_hooks_dict) derived from those constants with a parity test. AC-3 (negative): each ported change comes with a test that is red on the old code — the write through a tool the old matcher never saw (NotebookEdit into secret_scan, a serena relative_path into task_gate) is now REFUSED without an active task; 'the hook ran' is not evidence, the refusal is. AC-4: anchoring ^(?:...)$ is NOT ported and the reason is written: the contributor measured Claude Code 2.1.215 (a matcher of [A-Za-z0-9_|] is split on | and compared exactly; any other character switches the line to an unanchored regex), but Qwen Code and Codex read the same build_hooks_dict and their matcher semantics are unmeasured — anchoring could silently disable every hook on a host; instead a test pins the semantics: every non-empty matcher line is either pure exact-match alternation, or a regex-branch line whose alternatives cannot over-match any other tool name (measured against the tool universe). AC-5 (negative): before/after, the list of (tool, hook) interceptions is collected from build_hooks_dict and only grows — no working interception is lost. AC-6: the commit carries Co-Authored-By for the PR author; the reply for PR #5 is prepared for the owner; CHANGELOG EN/RU; verify signed.

## Plan

## Rollback

git revert коммита; ветка порта отдельная, в main вливается одним куском

## Journal

- 2026-08-25T15:35:26Z [planning] — AC1 ВЫПОЛНЕН В СЕССИИ #179, перенесён сюда из хэндоффа #179 без повторного разбора. Сверка велась по дереву 1.8, не по памяти. PR #5 (Okianiwa, 25 июля) предъявлял шесть охранников; ЧЕТЫРЕ ИЗ ШЕСТИ УЖЕ ЗАКРЫТЫ В 1.8. ТАБЛИЦА «утверждение PR #5 -> состояние в 1.8» (второй столбец — матчер из PR, третий — матчер сегодня в bootstrap/bootstrap_hooks.py): - task_gate: PR «Write|Edit» -> сегодня «Write|Edit|MultiEdit|NotebookEdit» -> ЗАКРЫТО - scope_write_gate: PR «Write|Edit|MultiEdit» -> сегодня «+NotebookEdit» -> ЗАКРЫТО - bash_firewall: PR «Bash» -> сегодня «Bash|PowerShell» через SHELL_MATCHER -> ЗАКРЫТО - git_push_gate: PR «Bash» -> сегодня «Bash|PowerShell» -> ЗАКРЫТО - secret_scan: PR «Write|Edit|MultiEdit» -> сегодня «+Bash|PowerShell», НО БЕЗ NotebookEdit -> ОТКРЫТО - memory_pretool_block: то же -> то же, БЕЗ NotebookEdit -> ОТКРЫТО Дополнительно закрыто в 1.8: mcp<2.0.0 запинен в requirements; shell_channel существует. ВТОРОЙ СЛОЙ (набор имён ВНУТРИ хука) сходится с матчером у scope_write_gate, но у двух оставшихся NotebookEdit выпал В ОБОИХ СЛОЯХ СРАЗУ: secret_scan.py:132 и _PATH_TOOLS в scripts/hooks/memory_pretool_block.py:62. Следствие фактическое: правка ноутбука сегодня не проходит НИ через секрет-сканер, НИ через маршрутизацию памяти. ОТКРЫТО, шесть пунктов (это и есть область AC2): 1. Якорения матчеров ^(?:...)$ нет нигде. Механизм в НАШЕМ дереве живой, а не гипотетический: матчер mcp__tausik-project__tausik_task_done (bootstrap/bootstrap_hooks.py:237) содержит дефисы, то есть по разбору PR уже сегодня исполняется неякоренным RegExp, а не сравнением на равенство. Практический вред сегодня нулевой (только пере-совпадение), но канал открыт. 2. MCP-редакторы serena и windows-mcp не покрыты ни одним хуком. 3. NotebookEdit выпал у secret_scan, memory_pretool_block._PATH_TOOLS и memory_posttool_audit._AUDITED_TOOLS. 4. auto_format сидит на матчере Write|Edit — без MultiEdit. 5. Единого источника имён инструментов НЕТ: четыре литеральных набора в четырёх хуках — _GATED_TOOLS, _PATH_TOOLS, _AUDITED_TOOLS и встроенный кортеж в secret_scan. Тот же класс «две копии одного правила», который релиз чинит на уровне каталогов. 6. task_gate читает из payload только file_path и notebook_path; path, relative_path, destination не читает. РАЗМЕР PR И ЕГО ФОРМА: GitHub отдаёт первые 100 файлов — 10222 добавленных строки, из них 8353 (81%) приходятся на подсистему autoloop, 39 файлов, к заявленной находке отношения не имеющую. Полный размер PR — 19399 строк. Находка внутри настоящая и ценная, но принять PR целиком означало бы принять несвязанную фичу под видом починки хуков. Отсюда форма переноса: берём находку, не берём autoloop; авторство сохраняем (конвенция #382, AC4). ПРОИСХОЖДЕНИЕ ЭТОЙ ЗАПИСИ: разбор сделан в #179, старт задачи тогда отказал гейт ёмкости (budget=90 exceeds remaining -1723/200), поэтому журнал остался пуст, а таблица уехала в хэндофф сессии. Восстановлена в #181. Побочная находка: хэндофф ЛЮБОЙ сессии, кроме последней, не читается ни CLI, ни MCP — session last-handoff отдаёт только свежайший, session show нет вовсе. Таблицу пришлось доставать из транскрипта IDE, то есть из-за пределов фреймворка.
- 2026-09-13T17:07:39Z [implementation] — AC-1 ✓ the table 'PR #5 claim -> state' stands in this journal (2026-08-25 note): four of six guards closed in 1.8, the fail-secure flip in 1.9 with credit; the six open points were the scope of this task. AC-2 ✓ one source: scripts/hooks/write_tools.py (BUILTIN_WRITE_TOOLS, MCP_WRITE_TOOLS from the PR, MCP_SHELL_TOOLS, PATH_FIELDS, edited_paths/edited_path); read by task_gate, scope_write_gate, secret_scan, memory_pretool_block, memory_posttool_audit, auto_format — tests/test_pr5_hook_coverage.py::TestOneListOfWriteTools::test_no_hook_keeps_a_private_copy_of_the_write_tool_list, ::test_edited_paths_reads_every_field_and_a_move_names_its_destination; shell_channel gains mcp__windows-mcp__PowerShell; bootstrap matchers (BUILTIN_WRITE_MATCHER, MCP_WRITE_MATCHER, MCP_SHELL_MATCHER, MCP_COVERAGE, with_mcp_registrations on Claude/Codex via build_hooks_dict and on the Qwen mirror) pinned to the package — ::test_bootstrap_restates_the_hooks_package_lists_exactly; MultiEdit on auto_format, NotebookEdit on secret_scan/memory_pretool_block/memory_posttool_audit — ::TestNothingStopsFiring::test_the_old_ledger_is_a_subset_of_the_new_one (gained pairs asserted). AC-3 ✓ (NEGATIVE) red on the OLD code, named plainly: the ledger (task_gate's body was already tool-agnostic — what it lacked was the registration); ::TestTheRefusalIsTheEvidence::test_secret_scan_sees_a_notebook_cell_in_strict_mode (old tuple returned 0 without looking — measured before wiring); ::test_memory_pretool_block_refuses_a_notebook_into_the_claude_memory_dir (old _PATH_TOOLS lacked NotebookEdit); ::test_a_move_out_of_the_project_is_gated_by_its_source and ::test_scope_acl_judges_the_source_of_a_move_too (the first cut judged the destination alone — review CRITICAL ×2, reproduced by the reviewer, fixed: every named path must be outside for task_gate's exemption, every in-project path is judged by the ACL). Also ::test_task_gate_refuses_the_write_without_a_task_and_allows_it_with_one[serena/NotebookEdit] — the refusal, with the same call passing once a task is active. AC-4 ✓ anchoring declined in writing (bootstrap_hooks.py comment with the PR's measurement: Claude Code 2.1.215, [A-Za-z0-9_|] = exact-match branch, anything else = unanchored regex; Qwen/Codex unmeasured) — ::TestTheMatcherSemanticsArePinnedNotAnchored::test_built_in_lines_stay_on_the_exact_match_branch, ::test_every_regex_branch_alternative_is_a_name_no_other_tool_contains (measured against a tool universe where 'Write'⊂TodoWrite and 'Bash'⊂BashOutput — ::test_the_universe_shows_why…), ::test_anchoring_is_declined_in_writing. AC-5 ✓ (NEGATIVE) the ledger only grows — ::test_the_old_ledger_is_a_subset_of_the_new_one; Qwen: ::test_qwen_mirror_gains_the_same_mcp_lines and ::test_a_wildcard_entry_gets_no_second_line_so_nothing_fires_twice (review HIGH: '*' is a wildcard, a second line would double-count). scripts/host_mechanisms._read_profile unions a hook's entries so the cross_model_parity gate keeps seeing host differences (tests/test_cross_model_parity_gate.py 26 passed). AC-6 ✓ commit carries Co-Authored-By: Okianiwa; PR #5 reply prepared for the owner; CHANGELOG EN/RU; docs/{en,ru}/hooks.md rows and enforcement-coverage.md (claim scoped to hook-bearing hosts — review MEDIUM); auto_format resolves a relative path against the project (review MEDIUM); RENAR manifest regenerated (v23) after the clause wording; verify run #2633 signed. 724 tests across the hook/bootstrap set + 1326 in the resolved scope; bootstrap_hooks.py at 488/500 lines (noted). Domain: a guard sees every tool its action is reachable with, the lists are one, and what is not ported is said and pinned rather than assumed.
