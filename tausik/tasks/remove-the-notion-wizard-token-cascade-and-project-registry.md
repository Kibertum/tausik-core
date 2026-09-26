---
slug: remove-the-notion-wizard-token-cascade-and-project-registry
title: "[1.9] Удалить мастер настройки Notion, каскад из трёх способов хранения токена и реестр проектов"
status: done
epic: release-19-renar-conformance
story: knowledge-sheds-notion-and-its-hygiene
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: "Удаление Notion-транспорта целиком по AC-1 с сохранением AC-2; генерируемые документы и счётчики; тесты удалённых модулей."
scope_exclude: "Не переписывать прозу docs/ru,en (это kb-docs-*), не менять общее локальное хранилище и его схему, не объединять проверки приватности (это unify-the-four-privacy-checks), не релизить."
relevant_files:
  - "scripts/project_parser.py"
  - "scripts/project.py"
  - "scripts/project_cli_snippet.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/knowledge_import.py"
  - "scripts/knowledge_mirror.py"
  - "scripts/brain_scrubbing.py"
  - "scripts/brain_universality.py"
  - "scripts/service_decide.py"
  - "scripts/mcp_tool_counts.py"
  - "scripts/doc_drift_common.py"
  - "scripts/doc_drift_scanners.py"
  - "scripts/doc_drift_tables.py"
  - "scripts/doc_drift_fixes.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_codex_mcp.py"
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap_kilo.py"
  - "bootstrap/bootstrap_opencode.py"
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_copy.py"
  - "bootstrap/bootstrap_config.py"
  - "bootstrap/bootstrap_modes.py"
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_hooks.py"
  - "tests/test_snippet_extract.py"
  - "tests/test_bootstrap_codex_mcp.py"
  - "tests/test_bootstrap_generate_mcp.py"
  - "tests/test_bootstrap_qwen.py"
  - "tests/test_bootstrap_kilo.py"
  - "tests/test_mcp_doc_tool_counts.py"
  - "tests/test_gen_doc_constants.py"
  - "tests/test_doc_table_count_subjects.py"
  - "tests/test_release_notes_1_9.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/brain_*.py"
  - "scripts/hooks/brain_*.py"
  - "scripts/knowledge_mirror.py"
  - "harness/claude/mcp/brain/**"
  - "harness/skills/**"
  - "harness/schemas/brain-artifact-card.schema.json"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser_brain.py"
  - "scripts/project_parser.py"
  - "scripts/project.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/project_cli_snippet.py"
  - "scripts/knowledge_import.py"
  - "scripts/service_knowledge.py"
  - "scripts/service_decide.py"
  - "scripts/mcp_tool_counts.py"
  - "scripts/doc_drift_*.py"
  - "bootstrap/*.py"
  - "tests/*.py"
  - "tests/conftest.py"
  - "docs/_generated/*"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - "docs/ru/mcp.md"
  - "docs/en/mcp.md"
  - "docs/README.md"
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
  - "docs/en/*.md"
  - "docs/ru/*.md"
  - README.md
  - README.ru.md
  - AGENTS.md
  - CLAUDE.md
  - ROADMAP.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/gates.json"
  - "tausik/tasks/*.md"
  - "tausik/stories/knowledge-sheds-notion-and-its-hygiene.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T14:45:50Z"
resolution: null
resolution_reason: null
---

## Goal

Вынесено из kb-notion-publisher решением #220, потому что не влезает в её бюджет и не даёт пользователю ничего наблюдаемого. Это ГИГИЕНА, а не возможность.

ОБЪЁМ, ИЗМЕРЕННЫЙ РАЗВЕДКОЙ, А НЕ ОЦЕНЁННЫЙ:
- Удалить целиком 6 файлов, 1425 строк: brain_init.py (368), brain_discovery.py (258), brain_project_registry.py (285), brain_init_join.py (190), brain_init_schemas.py (186), brain_init_create.py (138).
- Править ~9 файлов, ~200 строк: brain_runtime (_parse_dotenv 21 строка + resolve_brain_token 38), brain_config (compute_project_hash, валидация токена, ключи DEFAULT_BRAIN), brain_cli_ops (ветка init ~70), project_parser_brain (подпарсер ~60), brain_mcp_write (_resolve_project_name и project_hash), brain_scrubbing/brain_classifier/brain_status/brain_move, MCP handlers.
- Тесты: ~2200 строк. Целиком уходят test_brain_init.py (69 тестов, 1565 строк), test_brain_project_registry.py (29 тестов), test_brain_token_resolve.py (7 тестов); частично затронуты ещё 6-8 файлов.
- Документация: 18 файлов с ЗЕРКАЛАМИ ru/en, и в репозитории есть audit_translation_drift.py, который расхождение поймает.

ЛОВУШКА, НАЙДЕННАЯ РАЗВЕДКОЙ: реестр проектов нужен НЕ ТОЛЬКО мастеру. all_project_names() даёт union-блоклист скрабберу (brain_scrubbing, флаг union_with_registry), классификатору и brain_status — чтобы проект A не слил имя проекта B в общую вики. Удалять реестр, не заменив этот блоклист, значит ОСЛАБИТЬ приватность на границе публикации. Это отдельное решение внутри задачи, а не деталь.

ВТОРАЯ ЛОВУШКА: tests/conftest.py даёт фикстуру изоляции реестра для всего, что идёт через scrub_with_config(union_with_registry=True) — общий узел, ломает больше, чем видно по грепу. И tests/test_crosscutting_registry.py держит baseline из 30 записей с правилом «может только уменьшаться»: удаление файла из baseline способно его уронить.

НЕГАТИВНЫЙ СЦЕНАРИЙ ОБЯЗАТЕЛЕН: после удаления проект БЕЗ настроенного Notion обязан работать так же, как сейчас, а проект С настроенным — публиковать без мастера. Тест должен проверять ОБЕ ветки, иначе «удалили и вроде работает» окажется «удалили и тихо сломали публикацию у тех, кто ей пользуется».

## Acceptance Criteria

AC-1: the Notion transport is removed as a whole, not the wizard alone — decision #358 supersedes the pre-#358 goal text above. Removed: brain_notion_client, brain_notion_props, brain_sync, brain_init(+_create/_join/_schemas), brain_discovery, brain_project_registry, brain_runtime, brain_fallback, brain_mcp_read, brain_mcp_write, brain_move, brain_publish_flow, brain_publish_cli, brain_cli_ops, brain_status, brain_search, brain_schema, brain_hook_utils, brain_metrics_log, brain_artifact_card, brain_artifact_taxonomy, brain_classifier, brain_store_format; hooks brain_search_proactive and brain_post_webfetch; harness/claude/mcp/brain (server, handlers, tools); the /brain skill; the tausik brain CLI tree and project_parser_brain; the tausik-brain MCP registration in every bootstrap host profile; brain.* config keys and doctor's brain check; the tests of each removed module. AC-2: ~/.tausik-knowledge shared store and every --global path; knowledge_import (reads the local mirror file directly, no brain_* import); brain_universality(+_semantic) as the --global hint; brain_scrubbing as the single publication boundary the follow-up task unifies; brain_snippet_detect and tausik snippet detect. AC-3: a project with no Notion configured behaves byte-identically before and after on status, doctor, task start/done, decide --global and memory add --global — proven by the existing full lane plus a doctor run whose output no longer mentions Notion or brain. AC-4: the privacy blocklist that brain_project_registry.all_project_names fed to scrubbing is not silently lost: scrubbing keeps working on the shared-store path with an explicit, tested source of project names (the local project's own name), and the loss of the registry union is recorded as a scope note for unify-the-four-privacy-checks-into-one-publication-boundary. AC-5: bootstrap --ide all deploys no brain server, no brain skill, no brain hooks; bootstrap --check clean; gen_doc_constants regenerated (tool, hook, skill counts); cross_model_parity green; test_crosscutting_registry baseline honours its shrink-only rule. AC-6: generated/derived docs (cli.md, mcp reference, constants, README catalog counts) no longer list brain commands or tools; prose documentation (18 ru/en mirrors) is explicitly left to kb-docs-map/swarm/consistency and named so in the journal. AC-7: full pytest, ruff, mypy, dedupe (shrinks or holds), signed verify; CHANGELOG EN/RU entry under BREAKING.

## Plan

[{"step": "\u0420\u0430\u0437\u0432\u0435\u0434\u043a\u0430 \u0437\u0430\u043a\u0440\u044b\u0442\u0430 \u0437\u0430\u043c\u0435\u0440\u043e\u043c: \u0433\u0440\u0430\u0444 \u0438\u043c\u043f\u043e\u0440\u0442\u043e\u0432 brain_* (31 \u043c\u043e\u0434\u0443\u043b\u044c, 6778 \u0441\u0442\u0440\u043e\u043a), 2 \u0445\u0443\u043a\u0430, MCP brain, \u043d\u0430\u0432\u044b\u043a, 6 CLI-\u043f\u043e\u0434\u043a\u043e\u043c\u0430\u043d\u0434, \u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044f \u043d\u0430 5 \u0445\u043e\u0441\u0442\u0430\u0445, 30 \u0442\u0435\u0441\u0442\u043e\u0432\u044b\u0445 \u0444\u0430\u0439\u043b\u043e\u0432 (11367 \u0441\u0442\u0440\u043e\u043a), 55 doc-\u0444\u0430\u0439\u043b\u043e\u0432", "done": true}, {"step": "\u0421\u043d\u044f\u0442\u044c \u0442\u043e\u0447\u043a\u0438 \u0432\u0445\u043e\u0434\u0430: CLI brain, MCP brain + \u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044f \u0432\u043e \u0432\u0441\u0435\u0445 bootstrap-\u043f\u0440\u043e\u0444\u0438\u043b\u044f\u0445, \u0445\u0443\u043a\u0438, \u043d\u0430\u0432\u044b\u043a, doctor/snippet/config \u0432\u0435\u0442\u043a\u0438", "done": true}, {"step": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043c\u043e\u0434\u0443\u043b\u0438 \u0442\u0440\u0430\u043d\u0441\u043f\u043e\u0440\u0442\u0430 \u0438 \u0438\u0445 \u0442\u0435\u0441\u0442\u044b; \u043e\u0441\u0442\u0430\u0432\u0438\u0442\u044c knowledge_import, universality, scrubbing, snippet_detect \u0441 \u044f\u0432\u043d\u044b\u043c\u0438 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u0430\u043c\u0438", "done": true}, {"step": "\u041f\u0435\u0440\u0435\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043a\u043e\u043d\u0441\u0442\u0430\u043d\u0442\u044b/cli.md/\u043a\u0430\u0442\u0430\u043b\u043e\u0433\u0438, \u043f\u043e\u043f\u0440\u0430\u0432\u0438\u0442\u044c baseline'\u044b (crosscutting, dedupe, parity), \u043f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u043f\u043e\u043b\u043d\u044b\u0439 lane", "done": true}, {"step": "CHANGELOG BREAKING, \u0436\u0443\u0440\u043d\u0430\u043b \u0434\u043b\u044f kb-docs-*, signed verify", "done": true}]

## Rollback

git revert коммита(ов) удаления возвращает транспорт целиком; локальные зеркала ~/.tausik-brain/brain.db файлами не трогаются.

## Journal

- 2026-09-12T13:58:33Z [implementation] — Step 1 measurement (session #245): import graph over scripts/, hooks/, mcp/, bootstrap/: 31 brain_* modules / 6778 lines, non-brain users only project_cli_ops (CLI), project_cli_snippet (extract), knowledge_import + project_cli_doctor (brain_config path), service_knowledge (brain_universality hint). 30 tests/test_brain*.py = 11367 lines + 12 other test files mentioning Notion. tausik-brain MCP registered in bootstrap_generate (claude, cursor), bootstrap_codex_mcp, bootstrap_kilo, bootstrap_opencode, bootstrap_qwen. Docs: 55 files mention Notion (prose left to kb-docs-*). Budget 100 calls: the deletion is one command, the residue is edits in ~10 modules and the gates.
- 2026-09-12T14:36:59Z [implementation] — Steps 2-4 done in sessions #245-#246. Removed: 31 brain_* modules + brain_universality_semantic, 2 hooks, harness/claude/mcp/brain, harness/skills/brain, harness/schemas/brain-artifact-card.schema.json, 32 test files (test_snippet_brain_extract rewritten as test_snippet_extract). Entry points cut: tausik brain CLI + parser, snippet extract --scope brain + auto-propose, doctor brain server/skill/config checks, bootstrap registration on 5 hosts + brain hooks + skill gate + wizard prompt + is_brain_enabled, templates. Kept: knowledge_import (mirror path via new knowledge_mirror.py), brain_universality (regex only), brain_scrubbing (registry union removed), brain_snippet_detect, backend brain_events table (schema only; render_metrics tolerates empty). Retirement: every host generator drops a stale tausik-brain entry; Codex block is rewritten in place. Constants: hooks 24→22, skills_core 14→13, mcp_main 153→146, test_count floor 10787→10141; dedupe baseline 322/753→290/686; crosscutting baseline shrank by test_brain_mcp_installed_layout; doc-coverage floor 20→18 labels. Docs: README/AGENTS/architecture/mcp/cli/senar-matrix/agent-contract counts via gen_doc_constants --write; Shared Brain sections cut from cli.md and mcp.md EN/RU; whats-new-1.9 EN/RU got BREAKING #2. FOR kb-docs-map/swarm/consistency: 55 docs still mention Notion in prose (shared-brain.md, brain-artifact-taxonomy.md, quickstart, configuration, architecture diagrams, adding-new-ide, research notes) — those are theirs, not silently left. FOR unify-the-four-privacy-checks: scrub_with_config lost union_with_registry (registry gone); the cross-project blocklist must be rebuilt at the export boundary; brain_scrubbing currently has no live caller. Full lane: 9967 passed / 2 failed → fixed (notes page) → rerun below.
- 2026-09-12T14:40:05Z [implementation] — Root cause (other): decision #358 retired the subject — this is a removal, not a defect repair; the removal surface was measured (import graph, session #245) rather than estimated, and the one trap the pre-#358 goal named (the registry blocklist feeding scrubbing) is recorded as an explicit hand-off, not silently dropped.
- 2026-09-12T14:40:06Z [implementation] — AC verified: AC-1 ✓ every named module/hook/server/skill/CLI/registration/config/doctor item removed — grep -ri 'notion|brain_|tausik-brain' over scripts/ (non-kept), hooks/, harness/, bootstrap/ returns only knowledge_import, knowledge_mirror, brain_scrubbing, brain_universality, brain_snippet_detect and the brain_events schema. AC-2 ✓ kept items enumerated and green: test_knowledge_import, test_brain_universality (hint text updated), test_brain_scrubbing, test_brain_snippet_detect (draft tests removed with publish_flow). AC-3 ✓ Negative: doctor output has zero brain/notion lines and 23 OK/WARN/FAIL rows; full lane 9969 passed / 0 failed on the committed-to-be tree; status/task start/done/decide --global/memory add --global exercised by the same lane. AC-4 ✓ Negative: scrub_with_config keeps project_names from the caller's config (test_brain_scrubbing green); the registry union's loss is journaled for unify-the-four-privacy-checks. AC-5 ✓ bootstrap --ide all deploys no brain server/skill/hooks (.claude/mcp: codebase-rag, project; skills: 13), bootstrap --check clean, constants regenerated, cross_model_parity + hooks parity green, crosscutting baseline shrank by one; stale tausik-brain entries retired from .mcp.json/.cursor/.qwen/.kilocode/.codex with tests on every host. AC-6 ✓ cli.md/mcp.md EN+RU brain sections cut, README/AGENTS/docs counts regenerated; prose left to kb-docs-* and named in the journal. AC-7 ✓ ruff clean, mypy (commit hook set) clean, dedupe 290 groups (down from 322), CHANGELOG BREAKING EN/RU + whats-new-1.9 §2 EN/RU, signed verify below. Domain: a 1.8 consumer that bootstraps 1.9 loses the dead server entry instead of logging an MCP error on every IDE start.
- 2026-09-12T14:44:52Z [implementation] — AC-5: ✓ tests/test_bootstrap_generate_mcp.py::test_a_retired_managed_server_is_removed_while_user_servers_survive; ✓ tests/test_bootstrap_codex_mcp.py (regeneration in place, stale server gone); ✓ tests/test_bootstrap_qwen.py::test_qwen_removes_a_retired_managed_server; ✓ tests/test_bootstrap_kilo.py::test_a_retired_managed_server_is_removed_from_the_kilo_config; ✓ tests/test_bootstrap_hooks_parity.py. AC-2: ✓ tests/test_brain_universality.py::test_format_single_topic; ✓ tests/test_snippet_extract.py. AC-6: ✓ tests/test_mcp_doc_tool_counts.py; ✓ tests/test_release_notes_1_9.py. AC-7: ✓ verification_run #2491 (signed, ruff+pytest PASS, 109 files).
