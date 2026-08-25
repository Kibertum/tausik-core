---
slug: engine-claude-literals-followup
title: "Хвост литералов .claude в движке: пути скиптов/скиллов в хуках, ignore-globs аудита, кандидаты CLAUDE.md"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: complex
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: doctor-hardcodes-claude-dir
scope: "scripts/hooks/_common.py (+profile_dir/project_root helpers); scripts/hooks/session_start.py (делегирование _profile_dir); scripts/hooks/session_metrics.py (fix record_to_db); scripts/audit_orphan_files.py (динамические profile-globs); tests/test_doctor_multi_ide.py (_ALLOWED); tests/test_session_metrics_parse.py (+record_to_db); tests/test_audit_orphan_files.py (+all-profiles)"
scope_exclude: "scripts/project_cli_extra.py КОД (осознанный no-op — меняется только причина exemption); scripts/gate_filesize.py (.claude/mcp exempt — l26-filesize-gate-revisit); hooks/memory_pretool_block.py, service_knowledge_aggregates.py, service_replay.py (~/.claude HOME auto-memory — легитимно)"
relevant_files:
  - "scripts/audit_orphan_files.py"
  - "scripts/hooks/_common.py"
  - "scripts/hooks/session_metrics.py"
  - "scripts/hooks/session_start.py"
  - "tests/test_audit_orphan_files.py"
  - "tests/test_doctor_multi_ide.py"
  - "tests/test_session_metrics_parse.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T19:18:17Z"
---

## Goal

doctor-hardcodes-claude-dir закрыл горячий путь (doctor, роли, скиллы, сканеры, self-locating хуки) и поставил линт tests/test_doctor_multi_ide.py::TestNoNewClaudeLiterals, который держит остаток под явными исключениями с причинами. Остаток, который стоит добить отдельно: (1) hooks/session_metrics.py — путь к развёрнутому project.py собирается как project_root+'.claude/scripts', причём project_root вычислен тремя dirname от __file__ и на самом деле указывает на САМ каталог профиля, поэтому первый кандидат никогда не существует и всё работает случайно, через фолбэк на 'scripts/project.py'; надо переписать на self-locating путь по образцу session_start._profile_dir и убрать случайность; (2) audit_orphan_files.py ignore-globs '.claude/*' — на других IDE аудит считает сиротами развёрнутые файлы или наоборот; вывести из ide_utils.all_profile_dirs; (3) project_cli_extra.py кандидаты ['CLAUDE.md', '.claude/CLAUDE.md'] — обобщение до get_rules_file меняет поведение для AGENTS.md/.cursorrules, нужен осознанный выбор, а не механическая замена. НЕ включать сюда gate_filesize.py: его exempt на .claude/mcp/ — предмет l26-filesize-gate-revisit (именно он прячет 1289-строчный handlers.py от гейта). После каждого пункта — снять соответствующую запись из _ALLOWED линта, иначе исключение начнёт покрывать будущие добавления.

## Acceptance Criteria

1. session_metrics.record_to_db больше НЕ содержит мёртвый двойной литерал .claude/.claude: project.py находится через self-location (маркер профиля), а subprocess.cwd — истинный корень проекта (родитель профиля в deployed-раскладке), а не каталог профиля. Тест симулирует deployed-раскладку и утверждает resolved script path + cwd.
2. audit_orphan_files.DEFAULT_EXCLUDES покрывает ВСЕ профили из ide_utils.all_profile_dirs() (7 IDE), а не 3 хардкода; в файле не осталось строковых литералов .claude/.cursor/.qwen. Тест утверждает, что для каждого all_profile_dirs() есть globs `<p>/*` и `<p>/**/*`.
3. Логика self-location живёт ОДИН раз в hooks/_common.py (profile_dir/project_root); session_start._profile_dir делегирует туда (два потребителя — не 3-я приватная копия). Тест: _common.profile_dir() и session_start._profile_dir() согласованы.
4. _ALLOWED в test_doctor_multi_ide обновлён: audit_orphan_files.py удалён (литерала не осталось); session_metrics.py — причина ссылается только на ~/.claude/projects HOME-хранилище транскриптов; project_cli_extra.py — осознанное решение НЕ обобщать до get_rules_file, причина переименована в «documented ide_utils-unimportable fallback». test_no_stale_allowlist_entries зелёный.
5. Полный набор гейтов зелёный (pytest, линт TestNoNewClaudeLiterals + stale-allowlist), ноль новых warnings.
НЕГАТИВНЫЙ/ГРАНИЧНЫЙ: (а) source-раскладка (нет маркера профиля) → profile_dir() возвращает None, record_to_db резолвит <root>/scripts/project.py и cwd=<root>; (б) project.py отсутствует нигде → record_to_db возвращает False и пишет в stderr, БЕЗ падения (best-effort хук не роняет вызов).

## Plan

## Rollback

git revert коммита. Изменения аддитивны: новые хелперы в _common, генерация excludes из реестра, обновлённые причины exemption — нет схемы/миграции/конфига. Откат восстанавливает прежние литералы и хардкоды.

## Journal

- 2026-07-23T19:07:49Z [implementation] — Реализовано: (1) _common.profile_dir/project_root — единый дом self-location; session_start._profile_dir делегирует (2 потребителя). (2) record_to_db self-locate + cwd=истинный корень, мёртвый .claude/.claude убран. (3) audit_orphan_files globs из all_profile_dirs() (7 IDE). (4) _ALLOWED: audit_orphan дропнут, session_metrics/project_cli_extra переформулированы (осознанный no-op для project_cli_extra кода). Тесты: TestRecordToDbSelfLocation (deployed/source/missing), TestProfileDirAgreement, test_every_ide_profile_is_excluded. verify passed (pytest+hadolint), TestNoNewClaudeLiterals 4 passed. Заметка: _common.py=398 строк — 2 строки до filesize-лимита, кандидат на разгрузку следующей задачей.
- 2026-07-23T19:08:02Z [implementation] — AC verified: 1. ✓ tests/test_session_metrics_parse.py::TestRecordToDbSelfLocation::test_deployed_layout_uses_profile_script_and_root_cwd — cmd[1]=<profile>/scripts/project.py, cwd=<root>; мёртвый .claude/.claude убран (test_no_hardcoded_profile_in_deployed_script_join) 2. ✓ tests/test_audit_orphan_files.py::TestExclusion::test_every_ide_profile_is_excluded — все all_profile_dirs() покрыты; линт TestNoNewClaudeLiterals подтверждает отсутствие литерала в audit_orphan_files.py 3. ✓ tests/test_session_metrics_parse.py::TestProfileDirAgreement::test_common_and_session_start_agree — session_start._profile_dir()==_common.profile_dir(); логика в одном месте 4. ✓ tests/test_doctor_multi_ide.py::TestNoNewClaudeLiterals 4 passed (no-unexempted-literal + test_no_stale_allowlist_entries); _ALLOWED: audit_orphan дропнут, session_metrics/project_cli_extra переформулированы 5. ✓ tausik verify passed=True gates=[hadolint,pytest]; полный прогон затронутых файлов 35+ passed, 0 warnings 6. ✓ НЕГАТИВ (а) test_source_layout_uses_root_script — profile=None→<root>/scripts/project.py,cwd=<root>; (б) test_missing_project_py_returns_false_without_crash — False+stderr, без исключения
- 2026-07-23T19:09:06Z [implementation] — AC verified: 1. ✓ tests/test_session_metrics_parse.py::TestRecordToDbSelfLocation — deployed: cmd[1]=<profile>/scripts/project.py, cwd=<root>; мёртвый .claude/.claude убран 2. ✓ tests/test_audit_orphan_files.py::test_every_ide_profile_is_excluded — все all_profile_dirs() покрыты; TestNoNewClaudeLiterals: литерала в audit_orphan_files.py нет 3. ✓ TestProfileDirAgreement — session_start._profile_dir()==_common.profile_dir() 4. ✓ TestNoNewClaudeLiterals 4 passed (no-unexempted + stale-allowlist); _ALLOWED обновлён 5. ✓ verify passed gates=[hadolint,pytest]; bootstrap --ide all redeploy устранил drift 6. ✓ НЕГАТИВ (а) test_source_layout_uses_root_script; (б) test_missing_project_py_returns_false_without_crash — False+stderr без исключения
- 2026-07-23T19:09:24Z [implementation] — AC verified: 1. ✓ tests/test_session_metrics_parse.py::TestRecordToDbSelfLocation — deployed: cmd[1]=<profile>/scripts/project.py, cwd=<root>; .claude/.claude убран 2. ✓ test_every_ide_profile_is_excluded — all_profile_dirs() покрыты; литерала в audit_orphan_files.py нет 3. ✓ TestProfileDirAgreement — session_start делегирует _common.profile_dir 4. ✓ TestNoNewClaudeLiterals 4 passed; _ALLOWED обновлён (drop+relabel) 5. ✓ verify passed [hadolint,pytest]; bootstrap_drift+filesize зелёные 6. ✓ НЕГАТИВ (а) source→<root>/scripts; (б) missing→False+stderr без падения
- 2026-07-23T19:09:50Z [implementation] — AC1-6 pass: TestRecordToDbSelfLocation (deployed/source/missing), test_every_ide_profile_is_excluded, TestProfileDirAgreement, TestNoNewClaudeLiterals 4 passed, verify [hadolint,pytest] green, bootstrap_drift+filesize green
- 2026-07-23T19:13:03Z [implementation] — AC1-6 pass: TestRecordToDbSelfLocation(deployed/source/missing), test_every_ide_profile_is_excluded, TestProfileDirAgreement, TestNoNewClaudeLiterals 4 passed, bootstrap_drift+filesize green
- 2026-07-23T19:14:22Z [implementation] — AC1-6 pass: TestRecordToDbSelfLocation(deployed/source/missing), test_every_ide_profile_is_excluded, TestProfileDirAgreement, TestNoNewClaudeLiterals 4 passed, verify [hadolint,pytest] green, bootstrap_drift+filesize green
- 2026-07-23T19:18:05Z [implementation] — AC1-6 pass: TestRecordToDbSelfLocation(deployed/source/missing), test_every_ide_profile_is_excluded, TestProfileDirAgreement, TestNoNewClaudeLiterals 4 passed, verify run #1211 pytest PASS scope=high, bootstrap_drift+filesize green
- 2026-07-23T19:18:16Z [implementation] — AC1-6 pass: verify run #1211 pytest PASS scope=high; TestRecordToDbSelfLocation, test_every_ide_profile_is_excluded, TestProfileDirAgreement, TestNoNewClaudeLiterals 4 passed
- 2026-07-23T19:18:16Z [implementation] — Root cause (logic-error): doctor-hardcodes-claude-dir закрыл горячий путь, но оставил хвост — record_to_db считал project_root тремя dirname (=каталог профиля, не корень), мёртвый .claude/.claude кандидат жил за фолбэком; audit ignore-globs хардкодили 3 из 7 профилей. Prevention: self-location вынесен в единый _common.profile_dir/project_root (2 потребителя); профильные globs из ide_utils.all_profile_dirs(); линт TestNoNewClaudeLiterals + stale-allowlist сторожит новые литералы.
