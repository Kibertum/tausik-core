---
slug: audit-stale-docs-scope-noise
title: "audit_stale_docs сканирует gitignored пути и не исключает docs/research/"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/audit_tracked_files.py (новый), scripts/audit_stale_docs.py, scripts/audit_orphan_files.py, scripts/audit_unused_python.py, tests/test_audit_tracked_files.py (новый), существующие тесты этих аудитов"
scope_exclude: "scripts/audit_research_dump.py, scripts/audit_pytest_dedupe.py, .claude/** и прочие IDE-зеркала (генерируются bootstrap-ом), docs/** содержимое"
relevant_files:
  - "scripts/audit_tracked_files.py"
  - "scripts/audit_stale_docs.py"
  - "scripts/audit_orphan_files.py"
  - "scripts/audit_unused_python.py"
  - "tests/test_audit_tracked_files.py"
  - "docs/en/dev-doc-checks.md"
  - "docs/ru/dev-doc-checks.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-18T18:28:12Z"
---

## Goal

Обнаружено периодическим аудитом SENAR Rule 9.5 в сессии #112. audit_stale_docs выдаёт 3 кандидата, и все три — ложные, причём по двум разным причинам.

(1) docs/research/_internal/2026-06-12-...md попадает в отчёт, хотя каталог docs/research/_internal/ ГИТИГНОРИРОВАН (.gitignore:84) и файл не отслеживается (подтверждено git ls-files). Аудит ходит по файловой системе, а не по индексу git. Это создаёт вечный шум: файл по определению ни из чего не ссылается и «починить» его нельзя, потому что он намеренно локальный. Хуже: конвенция #176 требует, чтобы внутренние исследования не покидали gitignored каталог и не назывались кодовыми именами — а аудит печатает их ИМЕНА в отчёт, который может попасть в лог CI или в чужие глаза.

(2) v155-plan-kilo-zai.md и v156-qwen-portable-paths.md лежат в docs/research/ — это и есть настоящий дом исследований по конвенции #176. Но список исключающих глобов перечисляет docs/en/research/* и docs/ru/research/*, а сам docs/research/* — нет. Дампы исследований растут по замыслу и ни из чего не ссылаются, ровно как локализованные; исключение должно покрывать все три каталога.

Задача: (а) сузить обход до отслеживаемых git-ом файлов либо явно уважать .gitignore — предпочтительнее первое, оно заодно чинит и симметричные аудиты, если они ходят так же (проверить audit_orphan_files и audit_unused_python на ту же болезнь); (б) добавить docs/research/* в исключения. Негативный сценарий: аудит не должен падать вне git-репозитория и при пустом выводе git ls-files — деградировать до текущего поведения с предупреждением, а не с исключением.

Ценность: аудит с постоянным ложным выводом перестают читать, и настоящая находка тонет.

## Acceptance Criteria

AC-1: Появился общий хелпер получения списка отслеживаемых git-ом файлов (git ls-files -z), с покрытием тестом на happy-path. Возвращает None (а не пустое множество) при отсутствии git / вне репозитория — чтобы вызывающий отличил «git молчит» от «файлов нет».
AC-2: audit_stale_docs.collect_stale обходит только отслеживаемые файлы, когда git доступен. docs/research/_internal/*.md отсутствует в выводе — проверяется тестом на реальном дереве репозитория.
AC-3: docs/research/* добавлен в DEFAULT_EXCLUDES; v155-plan-kilo-zai.md и v156-qwen-portable-paths.md отсутствуют в выводе.
AC-4: python scripts/audit_stale_docs.py --check возвращает 0 на текущем дереве (ноль ложных кандидатов).
AC-5: audit_orphan_files и audit_unused_python используют тот же хелпер (симметричное лечение той же болезни).
AC-6 (негативный): при недоступности git (вне репозитория либо ошибка вызова) аудит деградирует до обхода ФС и печатает предупреждение в stderr, а не падает с исключением. Покрыто тестом с monkeypatch на хелпер (звать через модуль, не from-импортом — гоча сессии #114).
Negative: пустой вывод git ls-files трактуется как «git недоступен/пусто» и НЕ приводит к отчёту «все доки stale».
Evidence: tests/test_audit_tracked_files.py + обновлённые тесты аудитов, обе линии pytest (fast + slow).

## Plan

## Rollback

## Journal

- 2026-07-18T17:11:49Z [implementation] — Реализовано: scripts/audit_tracked_files.py (git ls-files -z, None=unknown вместо пустого множества), подключён в три аудита через module-import (не from-import, чтобы monkeypatch работал). docs/research/* + ** добавлены в DEFAULT_EXCLUDES. Аудит --check теперь exit 0 (было 3 ложных кандидата). Вывод соседних аудитов до/после сверен — оба были и остались пустыми, регрессии нет. 50 тестов зелёные. Доки EN/RU dev-doc-checks обновлены.
- 2026-07-18T18:27:42Z [implementation] — Верификация сессии #115. git diff просмотрен глазами до тестов (гоча #225) — литералы целы, все импорты модульные. Обе линии зелёные: pytest tests/ = 4746 passed/21 skipped (474с), pytest tests/ -m slow = 138 passed (868с). Три аудита --check exit 0, утечки имён из docs/research/_internal/ в вывод нет (проверено grep по _internal|v155|v156|kilo|zai|qwen). Найдена и закрыта дыра в тестах: три инвариантных теста (no_stale_candidate_is_untracked, internal_research_never_reported, research_dump_home_excluded) сформулированы как «в выводе нет плохого», а вывод на текущем дереве пуст — значит они проходили бы вхолостую, если бы collect_stale выродился в always-empty no-op. Добавлен положительный контроль TestPositiveControlWithGitAvailable: реальный git-репозиторий в tmp_path, tracked-но-нессылаемый docs/en/unreferenced.md ДОЛЖЕН попасть в вывод, а gitignored docs/research/_internal/local-note.md — нет. Мутационная проверка подтвердила: под no-op мутацией новый тест падает (вместе с AC-6-тестом), то есть краснеть умеет. 17 тестов в файле. Инцидент: откат мутации сделан через git checkout -- scripts/audit_stale_docs.py, что вернуло файл к HEAD и снесло все 28 вставок задачи. Восстановлено из копии, снятой до мутации; диффстат совпал, тесты и аудиты перепрогнаны зелёными. Записано в память #227.
- 2026-07-18T18:28:12Z [implementation] — AC-1: ✓ Общий хелпер scripts/audit_tracked_files.py:tracked_files (git ls-files -z --full-name), happy-path покрыт — tests/test_audit_tracked_files.py::TestTrackedFilesHappyPath::test_returns_tracked_paths_of_real_repo. Возвращает None (не пустое множество) при отсутствии git, вне репозитория, ненулевом exit и пустом выводе — tests/test_audit_tracked_files.py::TestTrackedFilesDegradation::test_outside_git_repo_returns_none, ::test_unusable_git_output_returns_none, ::test_subprocess_failure_returns_none_not_raise. AC-2: ✓ audit_stale_docs.collect_stale обходит только отслеживаемые файлы (_doc_files и _gather_inbound_text фильтруют через is_tracked); проверено на реальном дереве репозитория — tests/test_audit_tracked_files.py::TestRealRepoHasNoUntrackedCandidates::test_no_stale_candidate_is_untracked и ::test_internal_research_never_reported. AC-3: ✓ docs/research/* и docs/research/**/* добавлены в DEFAULT_EXCLUDES — tests/test_audit_tracked_files.py::TestRealRepoHasNoUntrackedCandidates::test_research_dump_home_excluded. Ни v155-plan-kilo-zai.md, ни v156-qwen-portable-paths.md в выводе нет. AC-4: ✓ python scripts/audit_stale_docs.py --check → exit 0 на текущем дереве, ноль кандидатов (было три ложных). AC-5: ✓ audit_orphan_files и audit_unused_python используют тот же хелпер (module-import + is_tracked на всех путях обхода); оба --check → exit 0, регрессии нет. AC-6: ✓ При недоступности git аудит деградирует до обхода ФС и печатает предупреждение в stderr, не падая — tests/test_audit_tracked_files.py::TestAuditDegradesGracefully::test_collect_stale_survives_unavailable_git. Патч поставлен через модуль (monkeypatch.setattr(audit_tracked_files, ...)), тест содержит assert called, поэтому не может пройти вхолостую. Negative: пустой вывод git ls-files трактуется как «git недоступен», а не как «файлов нет» — tests/test_audit_tracked_files.py::TestTrackedFilesDegradation::test_unusable_git_output_returns_none. Отчёт «все доки stale» невозможен: is_tracked при tracked is None допускает всё, то есть деградация расширяет обход, а не сужает его до нуля. Domain: статические аудиты документации и кода. Контракт деградации согласован с конвенцией #226 («неизвестно» ≠ «пусто») и #221; имена внутренних исследований не попадают в разделяемый вывод — конвенция #176. Checklist: обе линии pytest зелёные (tests/ = 4746 passed/21 skipped; tests/ -m slow = 138 passed). git diff просмотрен глазами до тестов. Добавлен положительный контроль TestPositiveControlWithGitAvailable, закрывающий вхолостую-проход трёх инвариантных тестов; мутационная проверка подтвердила, что он краснеет на no-op версии collect_stale. Инцидент с git checkout, снёсшим незакоммиченные правки, восстановлен из бэкапа и записан в память #227.
