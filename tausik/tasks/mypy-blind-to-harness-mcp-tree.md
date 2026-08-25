---
slug: mypy-blind-to-harness-mcp-tree
title: "mypy не видит harness/ — вся MCP-поверхность, которой пользуется агент, вне типовой проверки"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: "pyproject.toml (секция [tool.mypy] и overrides); harness/claude/mcp/**/*.py (аннотации, если область расширяется); CHANGELOG.md; CHANGELOG.ru.md"
scope_exclude: ".tausik/venv — установка любых пакетов ЗАПРЕЩЕНА (stdlib-only инвариант); поведение хендлеров; scripts/renar_conformance.py и project_cli_renar.py — код не трогаем, вопрос только в стабах"
relevant_files:
  - pyproject.toml
  - "scripts/mcp_reaper.py"
  - "tests/test_mypy_clean.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-28T08:44:28Z"
---

## Goal

Обнаружено при разрезе mcp-handlers-god-module-split. Проект гоняет `mypy scripts` (292 файла, чисто), а `harness/` в область не входит вообще. При этом именно `harness/claude/mcp/` — это поверхность, через которую агент разговаривает с фреймворком, и CLAUDE.md предписывает MCP-first, то есть непроверенный тип живёт ровно там, где цена ошибки выше всего.

Замер: `mypy` по одиннадцати модулям пакета mcp/project даёт 22 ошибки класса no-any-return. Пре-существующие — те же ошибки воспроизводятся на версии handlers.py из HEAD до разреза, так что разрез их не создал; он их только сделал видимыми, потому что заставил впервые прогнать mypy по этому дереву.

Второе, отдельное: `mypy scripts` целиком даёт 2 ошибки import-untyped на PyYAML (renar_conformance.py, project_cli_renar.py) — стабов нет, и ставить types-PyYAML нельзя: venv намеренно stdlib-only, это проверяет сам doctor («stdlib only — сторонние пакеты не утекли в venv»). Значит нужен не пакет стабов, а явное решение — override ignore_missing_imports для yaml, как уже сделано для memory_markers, либо аргументированный отказ.

Задача: (1) решить, входит ли harness/ в область mypy, и если да — как обходится коллизия имён модулей (mypy падает на двух server.py в разных директориях: codebase-rag/server.py и project/server.py, «Duplicate module named»); (2) закрыть или явно принять 22 no-any-return; (3) закрыть yaml-стабы override'ом без установки пакета. НЕ расширять область молча: гейт, который начнёт краснеть на всём дереве в день включения, выключат.

## Acceptance Criteria

AC1. Принято и ЗАПИСАНО решение по области mypy: либо harness/ входит (и тогда коллизия «Duplicate module named server» решена явно — explicit_package_bases / exclude / __init__.py, с обоснованием выбора), либо не входит (и тогда в pyproject.toml стоит комментарий, называющий причину, чтобы следующий читатель не считал это упущением).
AC2. Если harness/ входит: 22 ошибки no-any-return либо исправлены типизацией, либо накрыты override с обоснованием в комментарии — по образцу уже существующих override для project_service / backend_queries. Никакого глобального отключения проверки.
AC3. Две ошибки import-untyped на yaml закрыты override ignore_missing_imports (как memory_markers), БЕЗ установки types-PyYAML: venv обязан остаться stdlib-only, это инвариант, который проверяет doctor.
AC4. `mypy` в объявленной области выходит с кодом 0 и печатает Success.
AC5. НЕГАТИВ: doctor по-прежнему сообщает «stdlib only» — ни один сторонний пакет не добавлен в .tausik/venv.
AC6. Гейты зелёные, CHANGELOG.md + CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

git revert коммита: изменения — конфиг mypy в pyproject.toml плюс, возможно, аннотации типов. Отката поведения не требуется, типовые аннотации исполнением не читаются. Если расширение области окажется шумным — вернуть прежнюю область одним откатом секции [tool.mypy] и записать причину как dead end.

## Journal

- 2026-07-28T08:43:18Z [implementation] — Negative: (1) Сужение области обратно — новый тест test_declared_scope_covers_the_agent_facing_mcp_package падает, если harness/claude/mcp/project исчезнет из [tool.mypy] files; без него откат области прошёл бы молча. (2) Расхождение области конфига и области теста — устранено по причине, а не по симптому: тест больше не передаёт путь и вызывает mypy без аргумента, поэтому проверяемая область И ЕСТЬ объявленная; раньше это были два списка, и расширение конфига оставило бы новый код без проверки. (3) Нарушение инварианта venv — types-PyYAML НЕ установлен, состав .tausik/venv не изменён (проверено: doctor зелёный, pip list прежний), то есть починка типов не оплачена поломкой health-check. (4) Подавление вместо починки — единственная НЕ структурная ошибка (mcp_reaper.cached_enumerate -> Any) исправлена типом через TypeVar, а не override. Root cause (documentation): область типовой проверки была объявлена в двух местах — [tool.mypy] files и литерал 'scripts/' в аргументе теста, — поэтому расширение конфига не влекло расширения проверки, а сам красный жил незамеченным, потому что отчёт о прогоне брали из прозы хендоффа, а не из замера. Prevention: тест читает область из конфига (вызов без аргумента), базовая линия для «нет новых падений» берётся замером на HEAD в отдельном worktree, а не из чужого отчёта.
- 2026-07-28T08:44:25Z [implementation] — AC1 ✓ Решение принято и ЗАПИСАНО в самом pyproject.toml: harness/claude/mcp/project ВХОДИТ в [tool.mypy] files. Коллизия имён решена явно и с названной причиной — harness/claude/mcp/codebase-rag/ остаётся вне области, потому что там второй server.py, а два файла с одним верхнеуровневым именем заставляют mypy прерваться, не проверив НИЧЕГО («Duplicate module named», errors prevented further checking — воспроизведено). Комментарий называет задачу-владельца mcp-rag-server-module-split, в которой этот пакет войдёт в список. AC2 ✓ Из 21 всплывшей ошибки 20 — один структурный класс no-any-return от `svc: Any` на границе диспетчера; накрыты помодульным override с письменным обоснованием по образцу существующих override для project_service / backend_queries: пакет хендлеров НЕ ДОЛЖЕН импортировать ProjectService (эту зависимость и предотвращает разделение на самостоятельный пакет), а спрятанный за Any контракт (каждая запись возвращает str на вызов (svc, args)) пришпилен test_mcp_dispatch_surface.py. Двадцать первая — НЕ структурная и исправлена ТИПОМ, а не подавлением: mcp_reaper.cached_enumerate была объявлена `-> Any` и схлопывала тип вызывающего на границе кэша; обобщена через TypeVar _Enumerated, теперь тип вызывающего переживает round-trip. Глобального отключения проверок нет. AC3 ✓ Две ошибки import-untyped на yaml закрыты override ignore_missing_imports на модуле `yaml`, БЕЗ установки types-PyYAML. В комментарии записано различие, ради которого это не нарушает запрет теста на «помодульные ignore»: прощается не код репозитория, а отсутствие типовой информации в зависимости, которой мы сознательно не требуем (PyYAML лениво импортируется внутри except ModuleNotFoundError именно затем, чтобы CLI работал без неё). AC4 ✓ `mypy` в объявленной области: «Success: no issues found in 313 source files», exit=0. Было 292 файла и 2 ошибки; стало 313 файлов и ноль — область РАСШИРЕНА на 21 файл и одновременно зазеленела. AC5 ✓ НЕГАТИВ: состав .tausik/venv не изменён — ни одного пакета не установлено, types-PyYAML по-прежнему отсутствует, doctor зелёный. Инвариант stdlib-lean venv соблюдён; починка типов не оплачена поломкой health-check. AC6 ✓ Гейты PASS. tests/test_mypy_clean.py — 2 теста зелёные; ruff «All checks passed». CHANGELOG.md + CHANGELOG.ru.md — прозаические записи-зеркала, называющие обе находки и причину, по которой codebase-rag остаётся вне области. bootstrap --ide all прогнан (конвенция #321). Domain: ноль осмысленный, а не формальный. До правки `test_mypy_clean` был КРАСНЫМ на чистом HEAD (доказано отдельным git worktree с тем же venv), то есть проверка, заведённая ради превращения «нет новых ошибок» в проверяемый ноль, сама не выполнялась и об этом никто не знал — отчёт о прогоне брали из прозы хендоффа. Теперь проверяемая область И ЕСТЬ объявленная (тест вызывает mypy без аргумента), поэтому расхождение двух списков физически невозможно, а сужение области ловится отдельным тестом.
