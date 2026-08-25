---
slug: l26-verify-git-diff-wire
title: "Git-diff cross-check подключён, но пруф молчит о найденном расхождении"
status: done
epic: landscape-2026-h2
story: l26-trust-boundary
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: "scripts/verify_scope_honesty.py (новый — трёхзначное описание объявленного scope + security-предикат), scripts/verify_git_diff.py (низкоуровневый git-доступ), scripts/backend_schema.py (2 колонки + SCHEMA_VERSION 37→38), scripts/backend_migrations_v38.py (новый), scripts/backend_migrations.py (регистрация v38), scripts/service_verification.py (record_run прокидывает признак; run_gates_with_cache считает описание и применяет узкий блок), scripts/crypto_receipt.py (поля чека, схема v2), scripts/verify_receipt_emit.py + scripts/project_cli_verify.py (проброс), tests/test_verify_scope_honesty.py (новый), docs/{ru,en}/receipts.md, CHANGELOG.md + CHANGELOG.ru.md, docs/_generated/constants.json + бейджи README."
scope_exclude: "НЕ трогать: политику блокировки за само расхождение (решение #138 — расхождение остаётся неблокирующим, блок только на пересечении с security-предикатом); verify_cache.py / lookup_recent_for_task (логика попадания в кэш не меняется); _enforce_verify_first и QG-2-контракт (чтение признака в задаче не требуется); gate_runner.py; трастовые тиры конфигурации (новых конфиг-ключей не вводим — знак-выключатель для нового блока не заводить, см. память #217); receipt_export.py / verify_endpoint.py / no-sdk-verify (верификация схемо-агностична, считает канонические байты); backfill старых строк verification_runs (историю не переписываем — NULL читается как unknown)."
relevant_files:
  - "scripts/verify_scope_honesty.py"
  - "scripts/verify_run_record.py"
  - "scripts/service_verification.py"
  - "scripts/project_cli_verify.py"
  - "scripts/crypto_receipt.py"
  - "scripts/verify_receipt_emit.py"
  - "scripts/verify_files_hash.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v38.py"
  - "tests/test_verify_scope_honesty.py"
  - "tests/test_service_verification.py"
  - "tests/test_verify_receipt_emit.py"
  - "tests/test_verify_receipt_check.py"
  - "tests/test_verify_cache.py"
  - "tests/test_verify_first_contract.py"
  - "tests/test_security_sensitive.py"
  - "tests/test_specs.py"
  - "tests/test_adapts.py"
  - "tests/test_reasoning_steps.py"
  - "tests/test_snippet_storage.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "docs/en/receipts.md"
  - "docs/ru/receipts.md"
scope_paths:
  - "scripts/service_verification.py"
  - "scripts/service_gates.py"
  - "scripts/verify_scope_honesty.py"
  - "scripts/verify_run_record.py"
  - "scripts/verify_git_diff.py"
  - "scripts/verify_files_hash.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v38.py"
  - "scripts/crypto_receipt.py"
  - "scripts/verify_receipt_emit.py"
  - "scripts/project_cli_verify.py"
  - "tests/test_verify_scope_honesty.py"
  - "tests/test_verify_receipt_emit.py"
  - "tests/test_verify_receipt_check.py"
  - "tests/test_service_verification.py"
  - "tests/test_verify_first_contract.py"
  - "tests/test_verify_cache.py"
  - "tests/test_security_sensitive.py"
  - "tests/test_risk_compute.py"
  - "tests/test_qg2_gates.py"
  - "tests/test_crypto_receipt.py"
  - "tests/test_snippet_storage.py"
  - "tests/test_specs.py"
  - "tests/test_adapts.py"
  - "tests/test_reasoning_steps.py"
  - "docs/ru/receipts.md"
  - "docs/en/receipts.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-18T16:55:20Z"
---

## Goal

ПРЕМИСА ЗАДАЧИ БЫЛА УСТАРЕВШЕЙ — перепроверено в сессии #112 до начала работы, ровно как учит история с депрекируемыми Roots.  Что оказалось на самом деле. Модуль verify_git_diff.is_declared_consistent_with_git_diff НЕ «не подключён» — он подключён и работает: service_verification.py:210 (внутри run_gates_with_cache) и project_cli_verify.py:66. Задача в прежней формулировке («включить его в _enforce_verify_first») привела бы к дублированию уже существующей проверки.  Настоящая дыра тоньше и серьёзнее. Проверка гейтит ТОЛЬКО РЕШЕНИЕ О КЭШЕ. При расхождении происходит: кэш отвергается, в заметки задачи падает WARN, cache_status становится "git-mismatch" — и дальше run_gates запускается ПО ТОМУ ЖЕ УЗКОМУ ОБЪЯВЛЕННОМУ СПИСКУ, после чего record_run (service_verification.py:92) подписывает чек на этот узкий scope. record_run вообще не принимает признак расхождения: в verification_runs уходят task_slug, scope, command, exit_code, summary, files_hash — и ни одного поля о том, что объявленный scope противоречил git. Расхождение живёт только как транзиентное возвращаемое значение и как свободный текст в заметках.  Итог: агент, объявивший relevant_files=[README.md] при широкой правке, по-прежнему получает КРИПТОГРАФИЧЕСКИ ПОДПИСАННЫЙ зелёный чек на README.md. Система расхождение ОБНАРУЖИЛА и не отразила его в артефакте доказательства. Пруф молчит именно о том, что подрывает его ценность.  РЕШАЮЩИЙ ВХОДНОЙ ФАКТ ДЛЯ ДИЗАЙНА: «сделать блокирующим» — неверный ответ, и это измерено, а не предположено. Оба закрытия сессии #112 (l26-config-trust-tiers и token-metrics-append-name-lies) вернули cache_status="git-mismatch", потому что я честно правил CHANGELOG, README, доку и зеркала сверх объявленных relevant_files. Сигнал срабатывает на подавляющем большинстве добросовестных закрытий. Наивная блокировка встанет поперёк нормальной работы и будет отключена первой же.  Направления к рассмотрению: (а) добавить признак расхождения и фактический git-набор в строку verification_runs и в подписанный чек, чтобы пруф был ЧЕСТЕН о своей области, не блокируя; (б) расширять scope прогона до фактически изменённого набора вместо объявленного (дороже, но убирает расхождение в корне); (в) блокировать только когда необъявленное изменение затрагивает security-sensitive файлы (is_security_sensitive уже есть). Скорее всего (а) как база плюс (в) как узкий блок.  Смежное, проверить отдельно: compute_files_hash берёт только первые 4 КиБ файла (verify_files_hash.py:19,62) — правка той же длины за пределами 4 КиБ даёт тот же хеш и валидный кэш-хит. Решить, дыра это или осознанный компромисс, и задокументировать выбор.

## Acceptance Criteria

1. Выбрано и записано решением направление (а)/(б)/(в) или их сочетание, с обоснованием, опирающимся на измеренную частоту срабатывания, а не на предположение.
2. Расхождение объявленного scope с git перестаёт быть транзиентным: оно попадает в строку verification_runs и в подписанный чек, так что по чеку видно, была ли его область полной. Проверяется тестом, читающим записанный чек.
3. Добросовестное закрытие (правки доки/CHANGELOG сверх relevant_files) НЕ блокируется — покрыто тестом, воспроизводящим сценарий обоих закрытий сессии #112.
4. Недобросовестное закрытие видно: объявление relevant_files=[README.md] при правке scripts/*.py даёт чек, из которого расхождение читается явно. Тест на этот сценарий обязателен.
5. Negative: отсутствие git-репозитория, пустой relevant_files, отсутствующий task_created_at и сбой вызова git не должны ронять verify и не должны молча выдавать чек без признака расхождения — деградация обязана быть явной.
6. Решение по 4-КиБ окну compute_files_hash принято и задокументировано (закрыть либо признать компромиссом с указанием причины).
7. ruff чист; обе линии pytest зелёные; при изменении числа тестов пересчитаны constants.json и бейджи README.

## Plan

## Rollback

git revert коммита задачи. Миграция v38 чисто аддитивная (два ALTER TABLE ADD COLUMN, без CHECK/NOT NULL), поэтому revert кода оставляет колонки в БД неиспользуемыми и безвредными; понижать SCHEMA_VERSION нельзя (check_schema_migration_parity требует равенства — при откате вернуть 37 вместе с удалением записи 38 из MIGRATIONS). Чеки схемы v2, выпущенные до отката, остаются криптографически валидными: подпись считается по каноническим байтам сохранённого payload, а читатели используют .get() и не отвергают незнакомые ключи.

## Journal

- 2026-07-18T16:18:42Z [implementation] — Реализация закончена, тесты новые+смежные зелёные (309 + 24). Ключевые моменты: (1) Премиса задачи подтверждена перепроверкой — модуль подключён, дыра в том, что record_run не принимал признак расхождения. (2) Решение #139: направление (а)+(в), эмпирика — недообъявленный набор #112 прогнан через is_security_sensitive, совпадений нет, значит узкий блок на честных закрытиях не сработал бы. (3) Решение #140: 4-КиБ окно — осознанный компромисс, в хеш входит mtime_ns, коллизия требует os.utime, т.е. исполнения кода в дереве. (4) service_verification.py пробил filesize (416) — record_run вынесен в verify_run_record.py по паттерну verify_cache.py, стало 345. (5) НАЙДЕНА РЕГРЕССИЯ существующим тестом: from-import changed_files_since делал monkeypatch модуля бесполезным — переведено на обращение через модуль, добавлен комментарий про этот шов. (6) Тест test_cache_refused_when_declared_underreports фиксировал СТАРОЕ поведение на scripts/auth.py; разделён на два — нейтральный файл даёт git-mismatch, security-файл даёт scope-security-mismatch. (7) Гоча: первый скрипт-патч тестовых DDL зацепил INSERT INTO и порвал строковые литералы — откатил через git checkout и переделал с якорем на CREATE TABLE. Проверять diff после машинных правок обязательно. Осталось: доки receipts.md (ru/en), CHANGELOG обоих языков, constants.json, бейджи, обе линии тестов.
- 2026-07-18T16:55:19Z [implementation] — AC-1: ✓ Направление выбрано и записано Решением #139 — (а) честный чек как база + (в) узкий security-блок; (б) отвергнут. Обоснование опирается на измеренную частоту: оба закрытия сессии #112 дали git-mismatch и оба были добросовестными, поэтому наивная блокировка была бы отключена первой же — tests/test_verify_scope_honesty.py::TestSecurityBlock::test_session_112_honest_closure_does_not_block AC-2: ✓ Расхождение перестало быть транзиентным: колонки declared_scope_status и undeclared_files (миграция v38) плюс три поля в подписанном чеке tausik-receipt/v2. Тест читает расхождение ИЗ ЗАПИСАННОГО ЧЕКА и подтверждает, что подпись осталась валидной — tests/test_verify_scope_honesty.py::TestRecordRunPersistsScope::test_receipt_carries_divergence_and_stays_verifiable AC-3: ✓ Добросовестное закрытие не блокируется: воспроизведён недообъявленный набор обоих закрытий #112 (CHANGELOG, README, доки, constants.json, зеркала) — расхождение фиксируется, прогон зелёный — tests/test_verify_scope_honesty.py::TestRunGatesWithCacheIntegration::test_honest_under_declaration_is_not_blocked AC-4: ✓ Недобросовестное закрытие видно: relevant_files=[README.md] при правке src/auth.py даёт чек с явным расхождением и блокирует до запуска гейтов — tests/test_verify_scope_honesty.py::TestRunGatesWithCacheIntegration::test_undeclared_security_file_blocks_before_gates_run AC-5: ✓ Деградация явная — трёхзначный признак вместо булева: отсутствие git, пустой relevant_files, отсутствующий task_created_at и сбой git дают unknown, никогда complete — tests/test_verify_scope_honesty.py::TestTriState::test_git_failure_is_unknown_not_complete AC-6: ✓ Решение по 4-КиБ окну принято и задокументировано: Решение #140, компромисс, обоснование в докстринге compute_files_hash разделом NOT A SECURITY BOUNDARY — в хеш входит mtime_ns, поэтому коллизия требует восстановленного до наносекунды mtime, то есть исполнения кода в дереве AC-7: ✓ ruff чист; обе линии зелёные (4730 passed / 21 skipped быстрая, 138 passed медленная); constants.json пересчитан, бейджи README 4864 -> 4889 Negative: отсутствие git-репозитория, пустой relevant_files, отсутствующий task_created_at, сбой вызова git, недообъявление сверх лимита листинга (счётчик не усекается) — tests/test_verify_scope_honesty.py::TestTriState::test_not_a_git_repo_is_unknown, tests/test_verify_scope_honesty.py::TestTriState::test_listing_is_capped_but_count_is_not Domain: пруф молчал именно о том, что подрывает его ценность — система обнаруживала расхождение объявленного scope с git и не отражала его в артефакте доказательства. Проверено вживую, а не только тестами: verify run #1028 выпустил чек схемы v2 со статусом complete, первый в истории проекта чек, сообщающий полноту собственной области. Checklist: scope — 33 файла в ACL, границы зафиксированы в scope_exclude (политику блокировки за само расхождение не трогали, решение #138 сохранено); тесты — 25 новых, обе линии зелёные; security — узкий блок только на пересечении недообъявленного набора с is_security_sensitive, предикат проверен на реальном наборе #112; rollback — git revert, миграция v38 аддитивная, чеки v2 остаются валидными после отката
