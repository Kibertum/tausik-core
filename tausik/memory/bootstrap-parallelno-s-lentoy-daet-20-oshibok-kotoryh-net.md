---
slug: bootstrap-parallelno-s-lentoy-daet-20-oshibok-kotoryh-net
title: "bootstrap параллельно с лентой даёт 20 «ошибок», которых нет: он переписывает то, что тесты читают"
type: gotcha
tags:
  - bootstrap
  - flaky
  - pytest
  - race
  - windows
task: adapt-finding-categories-count-is-written-not-derived
edges: []
---

ЗАМЕР. В смене #201 полная лента, запущенная в фоне, дала 7685 passed / 26 skipped и ДВАДЦАТЬ errors. Изолированный повторный прогон любого из двадцати — зелёный. Причина не флаки: пока лента шла, я выполнил `python bootstrap/bootstrap.py --ide all`, который переписывает развёрнутые деревья (.claude, .cursor, .kilo, .opencode, .qwen), а тесты в этот момент их ЧИТАЛИ.

ПРИЗНАК, ПО КОТОРОМУ УЗНАЁТСЯ. Состав пострадавших говорит сам за себя: test_skills_maturity, test_skill_manager, test_skill_activate_supply_chain, test_skill_tool_references, test_gen_doc_constants, test_session_open_handler — всё, что читает развёрнутую копию, а не исходник. Если «ошибки» кучкуются вокруг skills и harness, а падений нет ни одного, ищи не флаки, а параллельную запись.

ОПАСНОСТЬ НЕ В ЛОЖНОЙ ТРЕВОГЕ, А В ОБРАТНОМ. Двадцать необъяснённых errors легко списать на среду и пойти дальше — при нулевой терпимости к ошибкам это ровно тот случай, когда «объяснил и забыл» превращается в базлайн. Разбор стоил одного чистого перегона (109 с) и дал ноль ошибок.

ПРАВИЛО. Пока идёт полная лента, дерево НЕ ТРОГАТЬ: ни bootstrap, ни ruff format, ни правки файлов. Фоновый прогон ленты не освобождает руки для работы с теми же файлами — он их занимает. Планируй bootstrap ДО ленты или ПОСЛЕ, но никогда во время.
