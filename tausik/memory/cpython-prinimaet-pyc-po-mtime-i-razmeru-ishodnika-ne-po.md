---
slug: cpython-prinimaet-pyc-po-mtime-i-razmeru-ishodnika-ne-po
title: "CPython принимает .pyc по mtime и размеру ИСХОДНИКА, не по пути: после переезда дерева трассировки называют старый адрес"
type: gotcha
tags: []
task: tracebacks-name-a-repository-path-that-does-not-exist
edges: []
---

tracebacks-name-a-repository-path-that-does-not-exist (#207): 527 .pyc из 2561 хранили co_filename D:\Work\Personal\claude\... — каталог, которого нет; трассировки через эти модули отправляли читателя в несуществующее дерево. Проверять чтением co_filename через marshal (пропустив 16 байт заголовка), сравнивать КАТАЛОГ с владельцем __pycache__ после normpath/normcase; относительный co_filename — не ложь. Держащая проверка — строка Stale bytecode в tausik doctor; чистка — doctor --fix-bytecode, только по списку. Разовое rm -rf __pycache__ не удерживает: кэш копился по трём версиям python и двум pytest.
