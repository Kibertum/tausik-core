---
slug: pytest-9-glotaet-preduprezhdeniya-plaginov-podnyatye-v
title: "pytest 9 глотает предупреждения плагинов, поднятые в pytest_configure — «его нет в выводе» не значит «его не поднимают»"
type: gotcha
tags:
  - measurement
  - pytest
  - warnings
task: pytest-asyncio-default-loop-scope-unset-warns-on-every-run
edges: []
---

ЗАМЕР #191. pytest-asyncio 1.3.0 в pytest_configure безусловно делает warnings.warn(PytestDeprecationWarning) про незаданный asyncio_default_fixture_loop_scope. В выводе pytest 9.0.2 этого предупреждения НЕТ ни в одном режиме: ни в обычном прогоне, ни с -rw, ни с -W always. Шапка при этом честно печатает asyncio_default_fixture_loop_scope=None, то есть ключ действительно не задан.

ПОЧЕМУ: предупреждение поднимается на стадии configure, до того как плагин warnings установил перехватчик, и уходит в пустоту.

КАК УВИДЕТЬ И РАЗЛИЧИТЬ: python -W error::DeprecationWarning -m pytest ... — фильтр интерпретатора действует раньше pytest и превращает вызов в INTERNALERROR с полной трассировкой до строки warnings.warn. Если он не сработал — предупреждение действительно не поднимается.

ЧТО ЭТО МЕНЯЕТ: задача, заведённая по строке «на КАЖДОМ прогоне печатается ...», может опираться на замер, устаревший вместе с версией pytest. Проверять надо не память, а сегодняшний вывод, и различать «не поднимают» от «поднимают, но не показывают» — это разные дефекты с разной ценой.
