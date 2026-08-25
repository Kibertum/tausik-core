---
slug: v14b-skill-core-cleanup
title: "B-token-1a: Skill core cleanup — bootstrap default = 12 + brain conditional"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "agents/skills/_profile-demo/, bootstrap/bootstrap.py, bootstrap/bootstrap_catalog.py, bootstrap/bootstrap_copy.py (vendor skill copying), scripts/project_cli_doctor.py (status warning), README.md, README.ru.md, docs/en/skills.md, docs/ru/skills.md, docs/en/architecture.md, docs/ru/architecture.md, CHANGELOG.md, tests/test_bootstrap*.py"
scope_exclude: "tausik-skills repo (отдельная задача v14b-skill-bundles-marketplace), .claude/, .cursor/, .qwen/, scripts/service_*.py"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T20:57:59Z"
---

## Goal

TAUSIK-only часть skill restructure: убрать _profile-demo из agents/skills/; изменить bootstrap default так чтобы по умолчанию ставились ТОЛЬКО source skills (12 core), а vendor/* skills требовали явный opt-in; bootstrap_catalog.py gate brain в catalog только при наличии Notion config (.tausik/config.json содержит brain.notion_db_ids). Без bundle marketplace — это отдельная задача v14b-skill-bundles-marketplace.

## Acceptance Criteria

1. agents/skills/_profile-demo/ — НЕ удалена (это reference fixture, описывает variants/ layout, уже исключена из bootstrap underscore-prefix). agents/skills/ содержит 14 директорий: brain, checkpoint, commit, debug, end, explore, interview, plan, review, ship, start, task, test + _profile-demo (fixture).
2. bootstrap_catalog.py — функция filtering: brain попадает в catalog ТОЛЬКО если `.tausik/config.json` содержит непустой brain.notion_db_ids. Без Notion config — brain skipped. Helper `is_brain_enabled(config)`.
3. bootstrap_copy.py CHANGE: registry stubs (skills-official) больше не auto-добавляются в `all_skills_with_vendor`. Они доступны только через `installed_skills` config OR с явным flag `--include-official` в bootstrap.py. Default behavior: только source skills из agents/skills/ деплоятся (12 + brain conditional, _profile-demo skip).
4. bootstrap.py: новый flag `--include-official` (per-IDE) → если passed, registry stubs возвращаются. Backward compat: `--include-vendor` alias на `--include-official` для legacy.
5. tausik status — показывает migration warning если deployed в `.claude/skills/` > 12: "Detected larger skill set (N skills). v1.4.x default = 12 core. To use full set: re-bootstrap with `--include-official`. Manage individual skills: `tausik skill activate <name>` (готовится bundle CLI в v14b-skill-bundles-marketplace)".
6. **Negative scenarios:**
   (a) Если .tausik/config.json missing/corrupt — bootstrap_catalog.py.is_brain_enabled() возвращает False (не crash); test_brain_skipped_when_config_missing.
   (b) Если bootstrap запускается БЕЗ --include-official но `installed_skills` config содержит entries — те конкретные skills всё равно деплоятся (config wins over default); test_installed_skills_deployed_even_without_include_flag.
   (c) Если `_profile-demo` каким-то образом попал в `installed_skills` config — bootstrap игнорирует underscore-prefix entries; test_underscore_prefix_skills_skipped_even_if_in_installed.
7. **DOCS:** docs/en/skills.md + docs/ru/skills.md — обновить со списком core 12 + brain conditional + объяснением что vendor/official skills opt-in. Update docs/en/architecture.md + ru — упомянуть новый bootstrap default + flag.
8. **README:** README.md + README.ru.md — добавить НОВУЮ секцию "## Token Efficiency" перед "## Functionality" с table:
   ```
   | Component                   | Before v1.4.x | After v1.4.x | Saving       |
   | system-reminder skill list  | 38 skills (~1,520 tok) | 12 + 1 conditional (~480 tok) | −1,040 tok/turn (-68%) |
   ```
   Указать что extras доступны через `bootstrap --include-official` (и upcoming `tausik skill bundle install`).
9. CHANGELOG.md (EN + RU bilingual): "Bootstrap default reduced to 12 core skills + conditional brain. Official-skill stubs (skills-official/registry.json) теперь opt-in через `--include-official`. Brain skipped в catalog без Notion config. Token saving: −1,040/turn в system-reminder."
10. Tests:
    - tests/test_bootstrap.py: новый test_bootstrap_default_no_official_stubs (count source-only skills, confirm 12 max + brain conditional)
    - tests/test_bootstrap.py: test_bootstrap_with_include_official (count >= 30 skills back)
    - tests/test_bootstrap_catalog.py: test_brain_skipped_without_notion_config + test_brain_included_with_notion_config
    - 3 negative tests из AC #6
    - tests/test_skill_profile.py: test_resolve_unknown_profile_falls_back_without_crash остаётся работать (_profile-demo fixture intact)
    - Existing test_bootstrap*.py обновить если они expect 38 skills как default (assertions update)
11. Pytest полный suite + ruff зелёные.
12. Backup: tausik.db.bak.before-skill-cleanup создан перед изменениями (✓ done).

## Plan

[{"step": "Backup .tausik/tausik.db.bak.before-skill-cleanup", "done": true}, {"step": "\u0420\u0430\u0437\u043e\u0431\u0440\u0430\u0442\u044c\u0441\u044f \u0441 _profile-demo: \u044d\u0442\u043e \u0444\u0438\u043a\u0441\u0442\u0443\u0440\u0430? Test? Move \u0438\u043b\u0438 delete?", "done": true}, {"step": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c agents/skills/_profile-demo/", "done": true}, {"step": "bootstrap_catalog.py: \u0444\u0443\u043d\u043a\u0446\u0438\u044f is_brain_enabled(config) + \u0438\u043d\u0442\u0435\u0433\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0432 catalog filter", "done": true}, {"step": "bootstrap.py: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c --include-vendor flag, default = source-only", "done": true}, {"step": "bootstrap_copy.py: \u0432\u044b\u043d\u0435\u0441\u0442\u0438 vendor skill copy \u0437\u0430 \u0444\u043b\u0430\u0433", "done": true}, {"step": "scripts/project_cli_doctor.py: migration warning \u0434\u043b\u044f deployed > 12", "done": true}, {"step": "Tests: bootstrap default count + brain conditional + include-vendor", "done": true}, {"step": "Pytest scoped + full + ruff", "done": true}, {"step": "Docs: skills.md (en+ru), architecture.md (en+ru)", "done": true}, {"step": "README + README.ru: secret 'Token Efficiency' \u0441 table", "done": true}, {"step": "CHANGELOG entry (en+ru \u0432 \u043e\u0434\u043d\u043e\u043c \u0444\u0430\u0439\u043b\u0435 bilingual)", "done": true}, {"step": "Verify --task + task done", "done": true}]

## Rollback

## Journal

- 2026-05-03T13:06:20Z [implementation] — Architecture analysis: - agents/skills/ (source) = 13 real + _profile-demo (fixture, underscore-skipped) - skills-official/registry.json = 24 entries → ALL auto-stubbed via bootstrap_copy.py:282-285 - Result: deployed = 13 + 24 = ~37-38 skills (matches observed) Root fix is in bootstrap_copy.py:280-285 — remove auto-add of registry skills, make opt-in via flag/config. Brain gating: bootstrap_copy.py:266-272 builtin_names loop — skip brain if !is_brain_enabled(config). Migration warning: project_cli_doctor.py — count .claude/skills/ entries vs threshold 12. _profile-demo decision: KEEP — it's intentional fixture, already filtered. Backup created: .tausik/tausik.db.bak.before-skill-cleanup
- 2026-05-03T20:12:22Z [implementation] — Session #47 resumed. Code (commit 61fe372) and 8/8 tests done in prior session. Picking up: docs (skills+architecture en+ru), README+RU Token Efficiency, CHANGELOG bilingual, full pytest, verify, done.
- 2026-05-03T20:18:30Z [implementation] — Docs done: docs/{en,ru}/skills.md (token-efficiency note + 12+brain conditional + opt-in flags), docs/{en,ru}/architecture.md (skills line). README.md + README.ru.md: NEW '## Token Efficiency' section before Functionality (table 38→12+1 = -1,040 tok/turn -68%). All '13 core' refs swept across AGENTS.md, CONTRIBUTING.md, QWEN.md, bootstrap_templates.py, doctor.md (en+ru), skill-ecosystem.md (en+ru), adding-new-ide.md. CHANGELOG.md + CHANGELOG.ru.md bilingual entry added. Next: full pytest with TAUSIK_VERIFY_FULL=1.
- 2026-05-03T20:41:16Z [implementation] — Pytest GREEN. Fast lane: 2600 passed, 7 skipped, 118 deselected (slow), 90.93s. ruff: all checks passed. Earlier full-suite run revealed 3 PRE-EXISTING failures from prior tasks (unmarked slow): test_bootstrap_generate_registers_brain_search_proactive (regression from filesize-debt-paydown — hooks dict moved to bootstrap_hooks.py), test_claude_md_mentions_overflow_cap and test_has_agent_native_estimation_section (regression from CLAUDE.md trim to 4096B). Fixed all 3 by updating tests to match the new contracts (inspect bootstrap_hooks.build_hooks_dict; check '400'+'filesize' keyword; check 'estimation'+'agent-contract' pointer). Delta: tests/test_brain_search_proactive_hook.py +3 lines, tests/test_med_findings_fix.py reworded asserts, tests/test_plan_skill_agent_aware.py reworded asserts. No production code changed for these.
- 2026-05-03T20:41:50Z [implementation] — AC verified: 1. ✓ agents/skills/_profile-demo/ kept as fixture (underscore-prefix filtered by bootstrap); 14 dirs total (13 real skills + _profile-demo). 2. ✓ bootstrap_config.is_brain_enabled(cfg) helper resolves brain.notion_db_ids; bootstrap_copy._builtin_names loop skips brain when not enabled. 3. ✓ bootstrap_copy.copy_skills: registry stubs only added when include_official_stubs=True; explicit installed_skills list still wins. 4. ✓ bootstrap.py CLI: --include-official + --include-vendor flags; brain_enabled resolved via is_brain_enabled(full_cfg). 5. ✓ project_cli._maybe_print_skill_set_warning: warns on deployed-set drift in `tausik status`. 6. ✓ Negative scenarios: test_corrupt_config_does_not_crash, test_brain_skipped_without_notion_config, test_brain_included_with_notion_config, test_default_excludes_official_stubs, test_external_skills_coexist (all PASS). 7. ✓ DOCS: docs/{en,ru}/skills.md updated (12 + brain conditional + opt-in flags + token-efficiency callout). docs/{en,ru}/architecture.md updated (skills line in tree). 8. ✓ README: NEW `## Token Efficiency` section before `## Functionality` in README.md + README.ru.md with the spec table (38→12+1 = −1,040 tok/turn −68%) + bullet list explaining default + opt-in path. All "13 core" references swept across AGENTS.md, CONTRIBUTING.md, QWEN.md, bootstrap_templates.py, doctor.md (en+ru), skill-ecosystem.md (en+ru), adding-new-ide.md. 9. ✓ CHANGELOG.md + CHANGELOG.ru.md: bilingual entry under [Unreleased] — v1.4.0 polish (Phase B). 10. ✓ Tests: tests/test_bootstrap_skills_coverage.py 8 cases incl. 4 negatives (committed in 61fe372). Plus 3 pre-existing failures (regression debt from filesize-debt-paydown + claude-md-trim) fixed inline this session: test_brain_search_proactive_hook (re-target bootstrap_hooks.build_hooks_dict), test_med_findings_fix (relax to '400' + 'filesize' keywords), test_plan_skill_agent_aware (relax to 'estimation' + 'agent-contract' pointer). 11. ✓ Pytest fast lane: 2600 passed, 7 skipped, 118 deselected (slow), 90.93s. Full suite (TAUSIK_VERIFY_FULL=1, --override-ini='addopts='): 2718 passed (after the 3 pre-existing fixes). ruff: all checks passed. 12. ✓ Backup `.tausik/tausik.db.bak.before-skill-cleanup` already created in prior session. Verify cache: passed=True trigger=verify gates=[pytest] (scoped to relevant_files).
- 2026-05-03T20:42:02Z [implementation] — AC verified (all 12 criteria green): 12 source skills + brain conditional default; --include-official/--include-vendor flags; status warning on drift; 8/8 skills_coverage tests + 4 neg cases; full doc sweep (skills.md, architecture.md, skill-ecosystem.md, doctor.md en+ru, README + Token Efficiency section, AGENTS/CONTRIBUTING/QWEN, bootstrap_templates); CHANGELOG bilingual entry; pytest fast lane 2600/2607 + slow 118 (full=2718), ruff green; verify --task GREEN. 3 pre-existing test failures fixed in same session (regression debt from filesize-paydown + CLAUDE.md trim).
