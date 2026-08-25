---
slug: v15p-doc-drift-gate
title: "[P1] Doc/code drift CI-gate: counts + MCP descriptions"
status: done
epic: v15-polish
story: v15p-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/mcp_tool_counts.py (mcp_descriptions_digest). scripts/gen_doc_constants.py (mcp_descriptions_hash в payload + scan_code_counts + --skip-code-counts). README.md/README.ru.md/AGENTS.md (починить hooks 19->21 дрейф). tests/test_gen_doc_constants*.py / test_doc_drift*.py. Регенерация constants.json."
scope_exclude: "code_counts.py счётчики (логика верна), skills cross-file scan (38-vendor неоднозначность — намеренно не добавляем), default_gates.py (CI уже enforce --check, не добавляем тяжёлый per-task гейт)"
relevant_files:
  - "scripts/gen_doc_constants.py"
  - "scripts/doc_drift_scanners.py"
  - "scripts/mcp_tool_counts.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T09:39:28Z"
---

## Goal

Расширить gen_doc_constants.py --check на счётчики stacks/agents/hooks/skills в README+docs (техдолг #4, #17) и добавить CI-gate на изменение MCP tool descriptions (cache-bust защита, техдолг #11). AC: drift «13 stacks vs 25» ловится гейтом; правка MCP description без явного флага падает в CI; gate в стандартном наборе verify.

## Acceptance Criteria

1. scan_code_counts ловит дрейф счётчиков (напр. "99 stacks" при stacks_count=25, "99 hooks" при 21) в CROSS_FILE_SCAN_TARGETS; включён в стандартный --check (skippable через --skip-code-counts). 2. mcp_descriptions_hash в constants.json: правка описания MCP-tool меняет хэш -> payload != existing -> --check падает (cache-bust защита, явный флаг = регенерация). 3. Ошибка/boundary: ложные срабатывания на "25 stack-aware checks"/"38 skills" НЕ ловятся (singular stack / skills исключены). 4. Существующий дрейф README hooks 19->21 починен, gen_doc_constants --check зелёный. 5. pytest зелёные.

## Plan

## Rollback

git revert коммита; удалить mcp_descriptions_hash из constants.json и регенерировать; сканы откатятся. README counts вернутся к 19 (но это был баг).

## Journal

- 2026-06-13T09:32:09Z [implementation] — scan_code_counts (stacks plural / hooks / review-agents, RU-формы), включён в стандартный --check + --skip-code-counts. mcp_descriptions_digest -> mcp_descriptions_hash в constants.json (правка описания бьёт --check). Singular 'stack-aware/guides' и '38 skills' исключены (negative-тесты). Починен реальный дрейф README hooks 19->21. Регенерация: test_count 3705->3752, бейджи обновлены. 31 тест зелёный, --check OK.
- 2026-06-13T09:32:17Z [implementation] — AC verified: 1. ✓ scan_code_counts ловит дрейф (test_scan_code_counts_flags_stacks_drift/hooks_drift) + skip-флаг (test_run_main_check_passes_with_skip_code_counts). 2. ✓ mcp_descriptions_hash бьёт --check (test_description_edit_busts_check). 3. ✓ negative: stack-aware/38 skills не ловятся (test_scan_code_counts_ignores_*). 4. ✓ README hooks 19->21 починен, --check OK. 5. ✓ pytest 31 passed.
- 2026-06-13T09:39:27Z [implementation] — Filesize: извлёк сканеры в doc_drift_scanners.py (295 строк), gen_doc_constants ре-экспортирует через __all__ (234 строки, обе < 400). 31 тест зелёный, --check OK.
