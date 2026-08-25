---
slug: os-chdir-v-teste-bez-vosstanovleniya-polnyy-progon-zelenyy
title: "os.chdir в тесте без восстановления: полный прогон зелёный, подмножество красное"
type: gotcha
tags:
  - "tests,pytest,isolation"
task: v2-verify-receipt-as-argument
edges: []
---

os.chdir(tmp_path) в тесте без восстановления уводит РАБОЧИЙ КАТАЛОГ ПРОЦЕССА на весь оставшийся прогон. Все последующие тесты остаются во временном каталоге, поэтому load_config() не находит .tausik/config.json и молча возвращает дефолты.

ЧЕМ КОВАРНО. Дефект зависит от ПОРЯДКА, а полный прогон идёт по алфавиту. В сессии #159 tests/test_verify_cache.py (пять непокрытых os.chdir) стоит по алфавиту ПОСЛЕ tests/test_gate_class_surface.py, поэтому полная батарея была зелёной — 6779 passed. А scoped-прогон verify сортирует файлы по своему правилу, там test_verify_cache идёт РАНЬШЕ, и test_named_exempt_files_are_exempt_and_documented падал с пустым frozenset() исключений filesize-гейта. То есть батарея зелёная, а подмножество ТЕХ ЖЕ тестов красное.

ЛЕЧЕНИЕ: monkeypatch.chdir(tmp_path) — pytest восстанавливает каталог на teardown. os.chdir в тестах не использовать никогда.

ДИАГНОСТИКА: если тест зелёный поодиночке и зелёный в полном прогоне, но красный в подмножестве — ищи не логику, а протечку глобального состояния между тестами: cwd, environ, sys.modules, кэш конфига.
