---
slug: ratchet-for-mcp-cli-surface-parity
title: "Расхождение MCP и CLI ловится глазами трижды подряд — нужен храповик, а не четвёртая точечная правка"
status: done
epic: release-1-11-3
story: release1113-quality-ratchets
complexity: complex
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/mcp_cli_parity.py (declared pair registry + known-loss ledger), tests/test_mcp_cli_surface_parity.py, docs en/ru, CHANGELOG en/ru"
scope_exclude: "harness/claude/mcp/project/handlers*.py and scripts/project_cli_*.py behaviour changes — the ratchet observes and compares, it does not fix handlers; each live loss it catches gets its own task"
relevant_files:
  - "scripts/mcp_cli_parity.py"
  - "tests/test_mcp_cli_surface_parity.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "tests/*.py"
  - "scripts/*.py"
  - "harness/claude/mcp/project/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T08:34:48Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#122"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Расхождение поверхности MCP и CLI ловится ПРОГОНОМ, а не чтением кода. Пара «инструмент MCP — команда CLI» объявлена списком, и тест требует, чтобы вывод MCP не терял того, что показывает CLI.

## Acceptance Criteria

AC1. ТРИ ИЗВЕСТНЫХ СЛУЧАЯ ОДНОГО КЛАССА названы в задаче как основание, а не как иллюстрация: (1) _handle_verify печатал список ИМЁН гейтов, из-за чего пропущенный гейт был неотличим от пройденного — исправлено ранее, и комментарий в коде прямо говорит 'this handler was the copy that extraction did not reach, and it is the copy the agent reads'; (2) handle_update_claudemd стирал хвост памяти при каждом /start — исправлено в сессии #177; (3) _handle_task_show скрывает scope_paths и rollback_plan — заведено отдельной задачей.
AC2. Существует объявленный СПИСОК пар «инструмент MCP — эквивалентная команда CLI». Пара, которой в списке нет, обязана быть либо добавлена, либо явно помечена как не имеющая эквивалента с причиной. Молчаливое отсутствие в списке — не ответ.
AC3. Тест сравнивает не байты, а ПОТЕРИ: каждое поле или строка, которую CLI показывает, а MCP нет, — провал. Обратное направление (MCP богаче) провалом НЕ является: у MCP свои конверты.
AC4. НЕГАТИВНЫЙ СЦЕНАРИЙ: храповик обязан ПОКРАСНЕТЬ на текущем task_show — это живой случай, а не выдуманный. Храповик, зелёный на дне заведения, не доказывает ничего.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: храповик НЕ имеет права требовать дословного совпадения текста. CLI печатает для человека, MCP отдаёт агенту; требование одинаковой формулировки заморозит оба и будет обходиться косметикой.
AC6. Если полный паритет по какой-то паре недостижим, это записано ЧИСЛОМ и причиной в самом списке, а не обойдено молчанием. Список с необъяснёнными исключениями хуже отсутствия списка: он выглядит как доказательство.

## Plan

## Rollback

git revert коммита: храповик удаляется, поведение команд не меняется — он ничего не исполняет, только сравнивает

## Journal

- 2026-10-07T08:27:32Z [implementation] — Ratchet implemented and live-red proof collected. scripts/mcp_cli_parity.py: PARITY covers all 149 live MCP tools (verified both directions against tools.TOOLS), 9 no-twin exceptions with reasons + written count, 15 driven read pairs, 6 not-driven read exceptions with reasons + count. tests/test_mcp_cli_surface_parity.py: 21 tests. AC4 proof — first full run went RED on the LIVE tausik_gates_status: CLI shows per-gate cmd column + meta-gate section (verify_first_contract, continuous_changelog, qg_0_readiness, renar_drift_1, renar_drift_7), MCP drops both; reproduced standalone with full seed, entered as 6 KNOWN_LOSSES entries with reasons; fix filed as mcp-gates-status-skryvaet-kolonku-cmd-i-sektsiyu in the same story (handler fixes excluded from this task by scope_exclude). Parser-reject iteration fixed 7 wrong guesses (stack info, skill repo add/list/remove, verify flags, snippet detect/extract has no search -> no-twin, memory_unblock does not exist). AC5 honoured: comparison is normalised field labels, never byte text.
- 2026-10-07T08:34:27Z [implementation] — AC verified. AC1 ✓: three named cases are the basis, named again in the module docstring — (1) _handle_verify printed gate NAMES (fixed earlier, the code comment still marks it as the copy the agent reads); (2) handle_update_claudemd erased the memory tail (fixed session #177); (3) _handle_task_show hid scope_paths/rollback_plan (fixed by mcp-task-show-hides-the-fields-the-agent-is-judged-by github#121, done 2026-09-23 — single list in scripts/task_detail_fields.py). AC2 ✓: PARITY in scripts/mcp_cli_parity.py declares 149 entries == live tools.TOOLS both directions (test_registry_covers_the_live_surface_exactly); 9 no-twin exceptions each carry a written reason (NO_TWIN_REASONS) with the count literal NO_TWIN_COUNT=9 asserted. AC3 ✓: the driver compares normalised field labels per pair; loss = CLI label absent in MCP output; MCP-richer direction is not a failure (asymmetric difference). AC4 ✓ NEGATIVE, live: the first full run went RED on the LIVE tausik_gates_status — six labels lost (cmd, renar_drift_1, renar_drift_7, verify_first_contract, continuous_changelog, qg_0_readiness), reproduced standalone on a planted project with full seed, recorded as six KNOWN_LOSSES entries with reasons; the handler fix is its own filed task mcp-gates-status-skryvaet-kolonku-cmd-i-sektsiyu in the same story — the ratchet is green through declared debt, not blindness. AC5 ✓ NEGATIVE: comparison is labels (lowercased, parenthesised noise stripped), never byte text; test_label_extraction_normalises_headers_and_noise pins it. AC6 ✓: NO_TWIN_COUNT=9 and NOT_DRIVEN_COUNT=6 are literals asserted against the dicts; every KNOWN_LOSSES entry carries a reason; an undeclared loss fails and a healed ledger entry fails — the ledger only shrinks. Verified by scoped verify run #3597 (PASS; 379 passed/16 skipped over 6 of 667 test files mapped from relevant_files; gates 8/9, hadolint N/A; handle 3597.4d0646bb03a4e585f5280c9dc37bf2e2). 3 files changed outside the receipt's scope belong to a parallel session (scripts/review_separation.py, tests/test_review_separation.py, new task file recognize-glm-5-2) — non-blocking, Decision #138. Changelog: [Unreleased] entries in CHANGELOG.md + CHANGELOG.ru.md.
- 2026-10-07T08:34:44Z [implementation] — NO-DEAD-END: red run #3595 was iteration hygiene, not a wrong approach — an unused noqa directive, one unformatted file, and bootstrap_drift firing because tausik_verify executed inside the stale MCP server process (pid 24888, self_check reported the drift at session open). Stripped the noqa, ruff-formatted, reran verify through the CLI in a fresh process: run #3597 PASS with a valid handle. The ratchet's own design (ledger + red-first proof) was never the failure.
- 2026-10-07T08:35:04Z [done] — Domain: the ratchet's comparison runs against the real service layer (ProjectService over a real SQLite DB) and the real CLI subprocess — the labels it compares are produced by the same code paths an agent hits in production, and the first catch (gates_status cmd column + meta-gates) was confirmed by standalone reproduction before entering the ledger.
