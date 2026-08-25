---
slug: brain-db-binding-ignores-path-case
title: "Гард принадлежности БД сравнивает пути без normcase: на Windows разный регистр диска молча выключает публикацию и врёт о причине"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: brain-decide-publishes-unclassified-rationale
scope: "scripts/service_knowledge.py (_is_working_project_db), tests/test_decide_classifies_what_it_publishes.py, CHANGELOG.md, CHANGELOG.ru.md. После правки scripts/ обязателен bootstrap --ide all."
scope_exclude: "НЕ трогать _local_reason и текст сообщений (правится причина, а не формулировка). НЕ трогать классификатор и гейт риска. НЕ разрезать service_knowledge.py — файл на 499 строках при лимите 500, разрез заведён отдельной задачей service-knowledge-one-line-from-filesize-gate и обязан идти ПЕРЕД этой правкой, если она добавляет строки."
relevant_files:
  - "scripts/service_decide.py"
  - "tests/test_decide_classifies_what_it_publishes.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-08-01T11:25:23Z"
---

## Goal

Найдено ревью сессии #153, подтверждено чтением обоих мест.

scripts/service_knowledge.py:271-272 — гард _is_working_project_db сравнивает os.path.abspath(self.be.db_path) с os.path.abspath(expected) БЕЗ os.path.normcase. На Windows d:\... и D:\... это один и тот же файл и разные строки.

В ЭТОМ ЖЕ РЕПОЗИТОРИИ ЕСТЬ ПРАВИЛЬНЫЙ ОБРАЗЕЦ. scripts/state_serialize.py:198-223 (assert_export_target) делает normcase перед сравнением и в комментарии называет ровно эту опасность: на регистронезависимых файловых системах легитимный путь, отличающийся только регистром, не должен отвергаться. Гард написан позже и образцу не следует. Память #83 фиксирует то же правило для этого проекта.

ПОСЛЕДСТВИЕ, и оно хуже, чем «не опубликовалось». Гард fail-closed, поэтому при расхождении регистра публикация молча выключается. При этом _local_reason:250-253 в этой ветке выдаёт сообщение «brain skipped — this service is not bound to the project DB, so an external publish would escape from a throwaway context». Пользователь работает в СВОЁМ проекте, а фреймворк объявляет его контекст одноразовым. То есть сообщение, специально переписанное в #152 ради честной причины, снова называет неверную.

ОБЪЁМ: normcase в сравнении, тест на пару путей, отличающихся регистром диска, падающий до фикса. Заодно рассмотреть realpath: симлинк на .tausik даёт ту же ложную отрицательность (отмечено ревью, отдельным дефектом не заводил — решить здесь и записать выбор).

## Acceptance Criteria

1. Сравнение путей в _is_working_project_db нормализует регистр так же, как это делает state_serialize.assert_export_target: пути, отличающиеся только регистром (d:\ против D:\), признаются одним файлом.
2. Тест на паре путей, различающихся регистром диска, доказывает, что публикация НЕ выключается, и падает до фикса.
3. Решение про symlink принято явно и записано: либо добавлен realpath, либо в докстринге зафиксировано, почему симлинк на .tausik сознательно считается чужой БД. Молчаливого умолчания не остаётся.
4. НЕГАТИВ: гард не ослаблен. Служба, привязанная к ДЕЙСТВИТЕЛЬНО чужой БД (другой каталог, а не другой регистр), по-прежнему не публикует; неразрешимая принадлежность по-прежнему fail-closed. Оба случая тестами — существующие test_foreign_db_never_publishes и test_unknown_db_provenance_fails_closed остаются зелёными.
5. НЕГАТИВ ПО СООБЩЕНИЮ: при отказе из-за регистра пользователь больше не получает утверждение про «throwaway context» о своём собственном проекте. Проверяется тем, что ветвь сообщения недостижима для пути, отличающегося только регистром.
6. Полный pytest зелёный, ruff и mypy чистые.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert. Изменение локализовано в одном сравнении путей плюс тест; схема и миграции не затрагиваются. Худший исход отката — возврат к текущему поведению (ложный отказ публикации при расхождении регистра), то есть отказ в сторону безопасности, без потери данных.

## Journal

- 2026-08-01T11:14:46Z [implementation] — Root cause (logic-error): гард сравнивал СТРОКИ путей там, где вопрос — тождество ФАЙЛА. os.path.abspath не сворачивает регистр и не разыменовывает ссылки, поэтому одно и то же имя в двух легитимных написаниях давало «не тот проект». Образец с правильным сравнением лежал в этом же репозитории (state_serialize.assert_export_target, память #83), гард написан позже и образцу не последовал. Prevention: сравнение вынесено в именованный предикат _same_file, чей докстринг разбирает ОБА источника разных написаний и явно доказывает безопасность направления — realpath и normcase способны слить только два написания одного файла, а два разных файла общего realpath иметь не могут; тесты закрывают обе стороны, включая чужой каталог. AC-ДОКАЗАТЕЛЬСТВА (записаны ДО verify). AC-1 ✓ _same_file делает normcase поверх realpath, как assert_export_target делает normcase перед сравнением; пути, различающиеся только регистром диска, признаются одним файлом. AC-2 ✓ ПРОВЕРЕНО ПРОГОНОМ, тест красный до фикса: временный возврат к os.path.abspath == os.path.abspath дал 3 failed, 1 passed в классе TestBindingGuardComparesFilesNotStrings; после отката пробы 35 passed. AC-3 ✓ symlink решён ДОБАВЛЕНИЕМ realpath, а не умолчанием: ссылка на базу проекта считается базой проекта, обоснование в докстринге _same_file, тест test_a_symlinked_tausik_dir_is_still_the_project (со skip там, где процесс не вправе создать ссылку — на Windows без Developer Mode; решение при этом всё равно записано, чего AC-3 и требует). AC-4 ✓ гард не ослаблен: test_a_genuinely_foreign_db_is_still_refused (другой каталог) — зелёный и НЕ краснел при пробе, то есть он проверяет именно то направление; test_foreign_db_never_publishes и test_unknown_db_provenance_fails_closed остались зелёными без правки. AC-5 ✓ test_the_throwaway_message_is_unreachable_for_a_casing_difference. ВАЖНО: первая редакция этого теста была ЗЕЛЁНОЙ И ПРИ ПРОБЕ — она подавала HEADLINE+RATIONALE, который классификатор сам маршрутизирует в local, поэтому гард не был решающим и тест проходил по постороннему поводу. Исправлено на кросс-проектный текст плюс утверждение «mirrored to brain»; после исправления тест краснеет при пробе, как и должен. Это ровно тот класс ложной зелени, который ловил property-тест этой же сессии. AC-6 — полный pytest идёт; ruff All checks passed, ruff format чисто, mypy Success 294 files. CHANGELOG ✓ EN + RU. Negative: помимо AC-4 закрыто и предупреждение компилятора. Первая редакция докстрингов содержала `d:\...` в обычной строке, что даёт DeprecationWarning: invalid escape sequence '\.' — три штуки в прогоне. Docstring'и переведены в raw (r"""), проверено py_compile с doraise по всем десяти изменённым за сессию файлам: all clean. Нулевая терпимость к предупреждениям означает и такие.
- 2026-08-01T11:25:21Z [implementation] — AC-1 ✓ _same_file: normcase поверх realpath, как в state_serialize.assert_export_target. AC-2 ✓ красное до фикса доказано прогоном: возврат к abspath==abspath дал 3 failed в TestBindingGuardComparesFilesNotStrings, после отката пробы 35 passed. AC-3 ✓ symlink решён добавлением realpath, обоснование в докстринге _same_file, тест со skip там, где процесс не вправе создать ссылку. AC-4 ✓ Negative: test_a_genuinely_foreign_db_is_still_refused зелёный и НЕ краснел при пробе (проверяет нужное направление); test_foreign_db_never_publishes и test_unknown_db_provenance_fails_closed зелёные без правки. AC-5 ✓ с исправлением ложной зелени: первая редакция теста проходила и при пробе, потому что классификатор сам маршрутизировал текст в local; переписана на кросс-проектный текст плюс утверждение «mirrored to brain». AC-6 ✓ полный pytest 6538 passed, 24 skipped, 0 failed; ruff чисто; ruff format чисто; mypy Success 294 files; bootstrap drift отсутствует; py_compile с doraise по всем изменённым файлам — предупреждений об escape-последовательностях нет. CHANGELOG EN+RU. Domain: дефект наблюдаем вне тестов — на Windows d:\ против D:\ возникает штатно от того, какой API выдал путь, и последствием была не только несостоявшаяся публикация, но и сообщение, объявлявшее собственный проект пользователя одноразовым контекстом.
- 2026-08-01T11:26:05Z [done] — ЧЕК-ЛИСТ ВЕРИФИКАЦИИ (SENAR Rule 5) — каждый критерий с именем теста или прогона, а не галочкой. AC-1: ✓ tests/test_decide_classifies_what_it_publishes.py::TestBindingGuardComparesFilesNotStrings::test_case_differing_drive_letter_is_the_same_project_db AC-2: ✓ ПРОГОН ПРОБЫ: временная замена _same_file на os.path.abspath(a)==os.path.abspath(b), команда `pytest tests/test_decide_classifies_what_it_publishes.py -k BindingGuard` -> «3 failed, 1 passed»; после отката пробы `pytest tests/test_decide_classifies_what_it_publishes.py tests/test_service_knowledge_decide.py` -> «35 passed». AC-3: ✓ tests/test_decide_classifies_what_it_publishes.py::TestBindingGuardComparesFilesNotStrings::test_a_symlinked_tausik_dir_is_still_the_project + докстринг scripts/service_decide.py::_same_file (решение записано и там, поэтому skip на платформе без права создавать ссылку не оставляет умолчания). AC-4: ✓ tests/test_decide_classifies_what_it_publishes.py::TestBindingGuardComparesFilesNotStrings::test_a_genuinely_foreign_db_is_still_refused (зелёный И при пробе — значит проверяет направление «не ослаблено»), ::test_foreign_db_never_publishes, ::test_unknown_db_provenance_fails_closed — обе без правки. AC-5: ✓ tests/test_decide_classifies_what_it_publishes.py::TestBindingGuardComparesFilesNotStrings::test_the_throwaway_message_is_unreachable_for_a_casing_difference (после исправления ложной зелени — см. память #360). AC-6: ✓ прогон `python -m pytest -q` -> «6538 passed, 24 skipped, 140 deselected in 618.51s»; `ruff check scripts/ tests/` -> All checks passed; `ruff format --check` -> 2 files already formatted; `mypy scripts/` -> Success: no issues found in 294 source files; `bootstrap.py --ide all` -> exit 0, гейт bootstrap_drift зелёный; `py_compile(doraise=True)` по десяти изменённым за сессию файлам -> all clean. ЗНАНИЕ ЗАФИКСИРОВАНО: память #360 (gotcha) — пробу фальсифицируемости проверять потестово, отрицательное утверждение дополнять положительным о том, что нужная ветка отработала.
