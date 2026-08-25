---
slug: v14b-review57-followups
title: "/review session #57 follow-ups: M1 brain.ignored pointer + M2 dedupe tausik_config_path + L1 split project_cli_extra.py"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "harness/skills/start/SKILL.md (M1 line); scripts/tausik_utils.py (helper); bootstrap/bootstrap.py + bootstrap_modes.py (use helper); harness/{claude,cursor}/mcp/project/handlers_skill.py (use helper); scripts/project_cli_extra.py + scripts/hooks/session_cleanup_check.py (use helper); tests/test_tausik_utils.py or new test for helper; CHANGELOG.md."
scope_exclude: "scripts/project_cli_extra.py содержание (split НЕ нужен — 353 строки); test_vendor.py:422 (test fixture, not production); bootstrap_config.py save_tausik_config (получает path как параметр, не дублирует логику); .claude/ generated copy (sync через bootstrap, не редактируем напрямую)."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T17:51:08Z"
---

## Goal

Close the three /review findings from session #57 that were deferred when fixing H1: M1 — add a brain.ignored:&lt;id&gt; pointer in agents/skills/start/SKILL.md so agents know which brain artifacts have been auto-skipped; M2 — dedupe the tausik_config_path helper that exists in both bootstrap.py and a sibling module; L1 — preempt scripts/project_cli_extra.py 399 → split before next change pushes it past the 400-line filesize gate.

## Acceptance Criteria

1. M1: harness/skills/start/SKILL.md "Brain primer — opt-in only" блок дополнен одной строкой про `brain.ignored:<id>` фильтр (тот же паттерн, что в /task /plan SKILL.md). После bootstrap копия в .claude/skills/start/SKILL.md синхронна.

2. M1 NEGATIVE: regression test (или явная ассерция в существующем test_skill_descriptions_length / новый минимальный тест) проверяет что слово "brain.ignored" присутствует в /start SKILL.md, чтобы будущие правки не откусили эту дисциплину.

3. M2: новый helper `tausik_config_path(project_dir: str) -> str` в scripts/tausik_utils.py — pure-stdlib функция, возвращает `os.path.join(project_dir, ".tausik", "config.json")`. Юнит-тест в tests/test_tausik_utils.py (или test_paths.py) проверяет нормальный путь и idempotency.

4. M2: все 6 production call-сайтов используют helper:
   - bootstrap/bootstrap.py:195
   - bootstrap/bootstrap_modes.py:231
   - harness/claude/mcp/project/handlers_skill.py:49
   - harness/cursor/mcp/project/handlers_skill.py:49
   - scripts/project_cli_extra.py:256
   - scripts/hooks/session_cleanup_check.py:28
   Inline `os.path.join(..., ".tausik", "config.json")` ноль матчей по grep после рефакторинга (исключая сам helper и тесты).

5. M2 NEGATIVE: тест test_vendor.py:422 (config_path в тестах) НЕ трогаем — тестовая фикстура tmp_dir, не production. Регрессия: pytest test_vendor.py + bootstrap unit tests ZER0 фейлов.

6. L1: project_cli_extra.py сейчас 353 строки (verify через `wc -l` или Python `len(open(...).readlines())`) — preempt-split НЕ требуется. Зафиксировать в task notes как no-op + check, что filesize gate всё ещё PASS для этого файла.

7. Bootstrap regenerate (`python bootstrap/bootstrap.py`) не падает; mirror sync тесты (test_med_findings_fix, test_plan_skill_agent_aware) PASS.

8. tausik verify --task v14b-review57-followups PASS; full pytest suite green (no regressions).

9. Docs: CHANGELOG entry под v1.4 polish (одна 1-2 строчная заметка про dedup).

## Plan

## Rollback

## Journal

- 2026-05-06T17:51:08Z [implementation] — AC verified: 1. ✓ harness/skills/start/SKILL.md +1 line documenting brain.ignored filter; bootstrap regenerated mirror in .claude/skills/start/SKILL.md 2. ✓ negative: tests/test_tausik_utils.py::test_start_skill_mentions_brain_ignored_filter 3. ✓ scripts/tausik_utils.py: tausik_config_path() helper + tests/test_tausik_utils.py::test_tausik_config_path_basic + idempotent + relative_dir 4. ✓ all 8 production sites use helper: bootstrap.py, bootstrap_modes.py (2 sites), handlers_skill.py x2, handlers.py x2 (cq-client), project_cli_extra.py, session_cleanup_check.py — verified by test_no_inline_duplicates_in_production 5. ✓ negative: test_vendor.py:422 untouched (test fixture); full pytest 2871 passed (5 new, 0 regressions) 6. ✓ project_cli_extra.py = 353 lines (verified via pytest); below 400-line gate; no split needed 7. ✓ bootstrap/bootstrap.py succeeds; mirror tests test_med_findings_fix + test_plan_skill_agent_aware PASS 8. ✓ tausik verify --task v14b-review57-followups exit=0; full pytest 2871 passed 7 skipped no regressions 9. ✓ CHANGELOG.md + CHANGELOG.ru.md updated with M1 + M2 + L1 no-op note
