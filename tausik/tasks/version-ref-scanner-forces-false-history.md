---
slug: version-ref-scanner-forces-false-history
title: "Сканер version-ref требует переписывать исторические ссылки и тем делает документацию ложной"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/doc_drift_scanners.py, docs/en/mcp.md, docs/ru/mcp.md, docs/en/architecture.md, docs/ru/architecture.md, tests/"
scope_exclude: "Не переписывать исторические утверждения ради зелёного гейта. Не трогать README-бейджи."
relevant_files:
  - "scripts/doc_drift_scanners.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "tests/test_gen_doc_constants.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T13:36:39Z"
---

## Goal

scan_version_refs флагует ЛЮБОЕ вхождение vX.Y в docs/{en,ru}/{architecture,mcp}.md, не отличая маркер «на текущую версию» от исторического «введено в v1.5». При бампе 1.5->1.6 гейт требует переписать 'tausik_session_open (v1.5)', 'hooks/check_docs.py (v1.5)' и 'как в релизах до v1.5' — все три утверждения после правки становятся ложными. Сам сканер это уже признаёт: MCP_COUNT_EXTRA_TARGETS исключает четыре других дока именно из-за 'legitimate historical version refs (e.g. introduced in v1.4)'. Решение: ссылка на версию означает «текущая» только в README.md, README.ru.md и CLAUDE.md; architecture.md и mcp.md документируют, в какой версии что появилось, и из version-скана исключаются (MCP-счётчики продолжают проверяться). Заодно убрать из них doc-wide маркеры версии, чтобы ничего не протухало молча.

## Acceptance Criteria

1) architecture.md и mcp.md исключены из version-скана, но остаются под MCP-count сканом. 2) Doc-wide маркеры версии из их заголовков убраны, чтобы не протухали молча. 3) Исторические ссылки ('введено в v1.5', 'до v1.5') сохранены дословно и не переписаны. 4) gen_doc_constants --check зелёный на версии 1.6.0. Негативные сценарии: 5) Ошибка, если version-ref в README.md перестал проверяться — там ссылка действительно означает текущую версию. 6) Ошибка, если MCP-счётчики в mcp.md перестали проверяться. 7) Ошибка, если какая-то историческая ссылка была изменена ради зелёного гейта.

## Plan

## Rollback

git checkout -- scripts/doc_drift_scanners.py docs/

## Journal

- 2026-07-10T13:36:28Z [implementation] — AC verified: 1. ✓ VERSION_SCAN_TARGETS не содержит architecture.md/mcp.md — test_history_docs_are_out_of_the_version_scan; они остаются в CROSS_FILE_SCAN_TARGETS ради MCP-счётчиков — test_history_docs_still_have_their_mcp_counts_checked. 2. ✓ Doc-wide маркеры убраны: '# TAUSIK MCP — Tool Reference (v1.5)' -> без версии, 'v1.5 actual count' -> 'current actual count', 'Modules in scripts/ (v1.5)' -> без версии; оба языка. 3. ✓ Исторические ссылки целы дословно: 'tausik_session_open (v1.5)' на строке 99, 'pre-v1.5 releases' на строке 27, 'hooks/check_docs.py (v1.5)' — ни одна не переписана; grep показывает 7/8/4/4 вхождений v1.5 в четырёх файлах. 4. ✓ gen_doc_constants --check зелёный на 1.6.0. 5. ✓ (негативный) test_stale_version_in_readme_is_still_caught: устаревшая v1.5 в README по-прежнему флагуется. 6. ✓ (негативный) test_history_docs_still_have_their_mcp_counts_checked. 7. ✓ (негативный) test_historical_marker_in_mcp_doc_is_not_flagged — маркер 'введено в v1.5' в mcp.md не поднимает тревогу. Root cause (logic-error): сканер сравнивал каждое вхождение vX.Y с текущей версией, хотя в документации версия встречается в двух разных смыслах — «сейчас у нас vX» и «это появилось в vX». Комментарий у MCP_COUNT_EXTRA_TARGETS показывает, что проблему уже осознавали ('legitimate historical version refs, e.g. introduced in v1.4') и решили исключением файлов — но architecture.md и mcp.md в тот список не попали. Гейт при бампе 1.5->1.6 потребовал от меня превратить три истинных утверждения в ложные, и я это сделал, прежде чем заметил и откатил. Prevention: гейт, который нельзя удовлетворить, не соврав, — хуже отсутствующего гейта; проверять надо только те места, где ссылка на версию действительно означает текущую. Полный прогон релиза: 4408 passed, 12 skipped, 0 failed.
