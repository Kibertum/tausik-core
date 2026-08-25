---
slug: zadacha-obyavivshaya-svoyu-zhe-proektsiyu-v-relevant-files
title: "Задача, объявившая свою же проекцию в relevant_files, не может попасть в кэш verify: запись AC-доказательства двигает files_hash"
type: gotcha
tags:
  - cache
  - dogfooding
  - qg2
  - state-export
  - task-done
  - verify-first
task: tausik-tree-gitattributes-lf
edges: []
---

Наступил в сессии #153 на задаче revise-kb-export-tasks-superseded.

МЕХАНИКА. Кэш verify ключуется на (slug, files_hash, подпись гейтов) — verify_cache.has_fresh_verify_run. Дерево tausik/ теперь перегенерируется автотриггером при ЛЮБОЙ durable-мутации, включая task log. Значит для задачи, у которой в relevant_files объявлены её собственные файлы проекции (типично для задач планирования, ревизии, правки карточек), последовательность «verify -> task log с доказательствами AC -> task done» ВСЕГДА даёт cache_status=miss: журнальная запись переписала объявленный файл и сдвинула хеш.

Это не дефект кэша: он честно замечает, что объявленная область изменилась после прогона. Дефект был бы обратный — принять устаревший зелёный.

ЧТО ДЕЛАТЬ. Прогон и закрытие идут ОДНОЙ цепочкой без журналирования между ними:
  tausik verify --task <slug> --relevant-files <все изменённые> [--no-tests-expected]
  затем сразу tausik task done <slug> --ac-verified --relevant-files <тот же список>
Все AC-доказательства пишутся в журнал ДО verify, а не между verify и done. Список файлов в обеих командах обязан совпадать буквально, иначе хеш снова разъедется.

СМЕЖНОЕ, замечено там же. `verify --task` без --relevant-files объявляет пустую область, и тогда все scoped-гейты пропускаются, а квитанция не сертифицирует ничего (verify-cache-empty-scope-hit, решение #226). А `verify --relevant-files` с файлами, не мапящимися на тесты, даёт scoped-прогон ОДНОГО тестового файла и печатает это прямым текстом — «SCOPE: scoped run over 1 of 366 test file(s)». Если критерий приёмки говорит «полный pytest зелёный», scoped-прогон его НЕ закрывает, и полный набор надо гонять отдельно.
