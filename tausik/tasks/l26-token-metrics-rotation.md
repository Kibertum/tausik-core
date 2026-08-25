---
slug: l26-token-metrics-rotation
title: "token_metrics.jsonl 199 МБ: нет ротации и дублируются строки"
status: done
epic: landscape-2026-h2
story: l26-hygiene
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/hooks/session_metrics.py"
  - "tests/test_token_metrics_rotation.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-18T11:10:00Z"
---

## Goal

Два дефекта в одном файле. (1) НЕТ РОТАЦИИ: append_token_rows (session_metrics.py:249-265) — голый open(path,a), ни max_bytes, ни prune. (2) ДУБЛИРОВАНИЕ: extract_token_rows (:185-246) перечитывает транскрипт с НУЛЕВОГО байта и дописывает ВСЕ строки заново; нет offset/seen-set/дедупа. SessionEnd-хук гонит это каждый раз, поэтому каждый повторный запуск сессии умножает её строки — отсюда 199 МБ. Нужно: смещение или seen-set по (session,tool_use_id), плюс ротация по размеру. Замерить размер до/после на реальном файле.

## Acceptance Criteria

1. ИДЕМПОТЕНТНОСТЬ: повторный прогон для той же сессии не умножает строки — набор строк сессии ЗАМЕНЯЕТСЯ, а не дописывается; двойной вызов даёт тот же файл, что и одинарный. 2. РОТАЦИЯ: файл не превышает заданный предел; при превышении отбрасываются самые старые строки, новейшие сохраняются. 3. ПАМЯТЬ: обработка существующего файла потоковая и ограничена пределом — недопустимо загружать в память файл целиком (сейчас он 191 МБ). 4. НЕГАТИВНЫЙ КЕЙС: некорректная (неразбираемая) строка в существующем файле пропускается без исключения, остальные данные не теряются. 5. НЕГАТИВНЫЙ КЕЙС: при отсутствующем файле или пустом наборе строк запись не падает. 6. АТОМАРНОСТЬ: запись через временный файл с последующей заменой, чтобы прерывание не оставило обрезанный файл метрик. 7. Разово ужать текущий файл 191 МБ. 8. Потребитель service_token_metrics.aggregate продолжает читать файл без изменений формата строк. 9. ruff чист; тесты зелёные на 3.11 и 3.13.

## Plan

## Rollback

git revert; запись возвращается к простому append без ротации

## Journal

- 2026-07-18T11:09:59Z [implementation] — AC-1: ✓ идемпотентность через ЗАМЕНУ строк сессии, а не дописывание — extract_token_rows и так отдаёт полный набор сессии, поэтому замена делает повтор идемпотентным по построению, без отслеживания смещений и идентичности строк — tests/test_token_metrics_rotation.py::TestIdempotence::test_rerunning_same_session_does_not_duplicate и ::test_other_sessions_are_preserved. AC-2: ✓ ротация с отбрасыванием старейших — tests/test_token_metrics_rotation.py::TestRotation::test_file_stays_under_cap_and_keeps_newest (39 сессий при пределе 4096 байт: новейшая выжила, старейшая отброшена). AC-3: ✓ потоковая обработка через deque с бюджетом байт, в память попадает не более предела, а не весь файл. AC-4: см. Negative. AC-5: см. Negative. AC-6: ✓ запись во временный файл + os.replace; tests/test_token_metrics_rotation.py::TestDegradation::test_no_temp_file_left_behind. AC-7: ✓ реальный файл сжат 190.5 МБ -> 8.5 МБ. AC-8: ✓ потребитель проверен вживую на сжатом файле: tausik metrics tokens отдал 18386 событий за 10 сессий, формат строк не менялся. AC-9: ✓ ruff чист, 8 passed на 3.11 И 3.13. Negative: неразбираемая строка пропускается без потери остальных данных — tests/test_token_metrics_rotation.py::TestDegradation::test_unparseable_line_is_skipped_not_fatal; пустой набор строк и отсутствующий каталог .tausik дают no-op без исключения — ::test_empty_rows_is_a_noop и ::test_missing_tausik_dir_is_a_noop. Domain: масштаб дефекта измерен на живых данных — 1034407 строк, из них уникальных 45934, то есть 95.6 процента файла были дублями от повторных прогонов SessionEnd-хука. После фикса .tausik уменьшился с 615 МБ (на старте сессии) до 347 МБ. Checklist: scope соблюдён (session_metrics.py + новый тест-файл), покрыты идемпотентность/ротация/деградация/атомарность, security surface нет, rollback = git revert (сжатие файла необратимо, но удалены только байт-идентичные дубли).
