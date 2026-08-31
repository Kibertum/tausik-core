---
slug: sverka-senar-9-5-v-199-dva-detektora-putayut-primer
title: "Сверка SENAR 9.5 в #199: два детектора путают пример-заглушку со ссылкой, остальное здорово"
type: context
tags:
  - audit
  - quality-sweep
  - senar-9-5
task: null
edges:
  - relation: supersedes
    target_type: memory
    target: zamer-196-audit-senar-9-5-mashinoy-44-nerezolvyaschihsya
---

СВЕРКА ПРОВЕДЕНА В #199 (просрочка была 3 смены). Что прогонялось живьём, а не читалось: doctor, gates status, memory lint (+--apply), audit vendors, audit research, audit evidence, полная лента, mypy.
ИТОГ ПО ЗДОРОВЬЮ: doctor — All clean (WARN о шести сиротах устранён переносом под story renar-debt-implemented-wrong в начале смены). Лента 7567 passed, 24 skipped, 0 failed. mypy 349 файлов OK. Гейты 17 зарегистрированы, 17 резолвятся.
ПАМЯТЬ: memory lint --apply заархивировал 4 superseded (#303, #421, #441, #466); было 11 находок, стало 7. Остаток — advisory stale_file.
ГЛАВНАЯ НАХОДКА СВЕРКИ, ОБЩАЯ ДЛЯ ДВУХ ДЕТЕКТОРОВ: ни memory lint, ни audit evidence не отличают ССЫЛКУ от УПОМИНАНИЯ-ПРИМЕРА. В линте 3 ложных из 7 (43%): память ПРО отсутствие пути помечается сгнившей за то, что путь называет; gitignored-файл считается пропавшим. В audit evidence счётчик NEVER_EXISTED=25 набит заглушками test_foo.py / test_x.py / test_does_not_exist.py, которые цитируют задачи, чей ПРЕДМЕТ — поддельные цитаты. Заведена задача memory-lint-flags-absent-path-that-is-the-memorys-subject (complex) на ОДИН корень, а не на два симптома.
ЗАМЕР ЦИТАТ (обновляет #463): 1267 закрытых задач, 541 цитирует тест, 3041 цитата / 1107 уникальных, резолвятся 1063, ROTTED 19, NEVER_EXISTED 25. Числа те же, что в #196, но ТОЛКОВАНИЕ изменилось: значительная часть NEVER_EXISTED — намеренные заглушки, а не подделка доказательств.
ДОЛГ, ОСТАВЛЕННЫЙ СОЗНАТЕЛЬНО: 5 неиспользуемых vendor-репозиториев (anthropic-official, polyakov, seo, trailofbits, ui-ux-pro-max) и 2 research-дампа, теперь 108 дней. Обе команды аудита read-only и никогда не удаляют; удаление чужих скилл-репозиториев — решение владельца, не агента.
ЗАВЕДЕНО ЗА СВЕРКУ 3 ЗАДАЧИ: дефект двух детекторов (complex); неверная подсказка CLI у task add (medium); subprocess без encoding (simple, ЗАКРЫТА в этой же смене).
