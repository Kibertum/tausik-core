---
slug: v15p-release-150
title: "[P0-final] Release v1.5.0 — bump, CHANGELOG, docs sync"
status: done
epic: v15-polish
story: v15p-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "pyproject.toml (bump 1.4.2→1.5.0), CHANGELOG.md, README.md (бейджи), bootstrap/constants.json + gen_doc_constants (version-sync), CLAUDE.md. Локальный release-prep + финальный pytest/bootstrap."
scope_exclude: "Фактический git push / теги / GitHub-релизы — отложены на батч push-ok в конце (решение пользователя). GitHub mirror НЕ пушить (отстаёт)."
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tests/test_rule2_scope_hardgate.py"
  - pyproject.toml
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T23:08:13Z"
---

## Goal

FINAL publish gate for v1.5.0 — RE-OPENED because the release was NOT published. The prep ran earlier (version bump to 1.5.0, CHANGELOG [1.5.0] section, docs sync), but the actual publication never happened: no git tag v1.5.0, no push to the public GitHub mirror, no announce. Do this LAST, only after all v1.5 work-streams are done (model-routing P1, snippet-system, polish debt/defects, orchestrator). On publish day: verify/refresh the CHANGELOG [1.5.0] date, move [Unreleased] (RENAR Phase 0-1) appropriately, tag, push public.

## Acceptance Criteria

1. pyproject version 1.4.2→1.5.0; все vX.Y-ссылки синхронны (gen_doc_constants --check зелёный после bump+регенерации constants). 2. CHANGELOG.md: секция 1.5.0 покрывает эпик evidence-attestation (911d4e6..8200503) + сессию #80 (cbfa9a3..22c48c4) + rule7 + stdin-fix. 3. README-бейджи test_count обновлены (вырос на +15). 4. Финальный pytest зелёный; bootstrap из fresh clone работает (smoke). 5. Negative/boundary: gen_doc_constants --check ловит ЛЮБУЮ рассинхронизированную vX.Y-ссылку (fail если осталась 1.4.x); doctor зелёный.

## Plan

## Rollback

git revert коммита bump (версия/CHANGELOG/constants все в git, ревертабельны); нет DB-миграций; теги не создаются до явного push-ok, откатывать нечего на remote.

## Journal

- 2026-06-13T12:37:42Z [implementation] — Release prep: pyproject 1.4.2→1.5.0 + tausik_version.py (был застрявший 1.4.0). Doc version-sync: bulk v1.4→v1.5 в 6 файлах (README×2, docs/{en,ru}/{architecture,mcp}.md), регенерация constants.json, --check зелёный. README-бейджи 3803→3818. CHANGELOG×2 [1.5.0] (эпик evidence-attestation + #80 + rule7 + stdin-fix), Planned→v1.6. Баннеры README переписаны под реальные темы 1.5. Bootstrap --ide all (161 скрипт×3, .claude gitignored). doctor All clean. Попутно починил 2 пред-существующих красных теста из #80: test_no_warning_within_budget (Rule 5 checklist hardgate на substantial — добавил checklist в _seed_active_task), test_mcp_mirrors_in_sync (cursor-harness отставал — memory_lint пропущен в #80, синкнул tools.py+handlers.py). Checklist: scope ✓, tests ✓ (полный pytest), edge-cases (version-sync negative — --check ловит любой 1.4.x), no security surface.
- 2026-06-13T12:45:37Z [implementation] — AC verified: 1. ✓ pyproject+tausik_version 1.5.0, gen_doc_constants --check зелёный после bump+регенерации. 2. ✓ CHANGELOG×2 [1.5.0] (evidence-attestation 911d4e6..8200503 + #80 cbfa9a3..22c48c4 + rule7 + stdin-fix). 3. ✓ README-бейджи 3803→3818. 4. ✓ полный pytest 3690 passed/0 failed; bootstrap --ide all + doctor All clean (bootstrap drift none). 5. ✓ negative: --check ловит любой 1.4.x (доказано: 57 ref'ов флагнуто до починки), doctor зелёный. Checklist: scope/tests/edge-cases/security залогированы.
- 2026-06-14T23:08:05Z [implementation] — AC verified: 1. ✓ pyproject + tausik_version 1.5.0; gen_doc_constants --check green. 2. ✓ CHANGELOG.md + .ru.md folded [Unreleased]→[1.5.0] — 2026-06-15 (evidence-attestation + SENAR + reliability + AIDD + memory + BLE001 + orchestrator-worker + RENAR-lite). 3. ✓ README badges synced (4330 tests, coverage 76%). 4. ✓ full pytest green (4201 passed, 8 skipped) + ruff/mypy clean (210). 5. ✓ negative: gen_doc_constants --check catches any stale version ref. PUBLISHED: commit 7b5bbe6 pushed to main; git tag v1.5.0 (annotated) pushed to public github.com/Kibertum/tausik-core; GitHub Release created (releases/tag/v1.5.0). Domain: the 1.5.0 tag + release are live on the public mirror; users can now install the hardened release. Irreversible publish done on explicit user go.
