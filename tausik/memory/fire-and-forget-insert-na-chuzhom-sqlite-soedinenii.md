---
slug: fire-and-forget-insert-na-chuzhom-sqlite-soedinenii
title: "Fire-and-forget INSERT на ЧУЖОМ sqlite-соединении оставляет открытую транзакцию → коллизия с BEGIN IMMEDIATE"
type: gotcha
tags:
  - best-effort
  - fail-open
  - l26-bypass-telemetry
  - sqlite
  - telemetry
  - transaction
task: l26-bypass-telemetry
edges: []
---

Найдено адверс-ревью в l26-bypass-telemetry (CRITICAL). При добавлении «best-effort» аудит-записи в поток НЕЛЬЗЯ писать raw INSERT в переданное вызывающим соединение (conn) БЕЗ commit, рассчитывая «уедет на общем commit потока».

ПОЧЕМУ: Python sqlite3 при isolation_level по умолчанию (deferred) на любом DML НЕЯВНО открывает транзакцию, которая висит до commit/rollback. Если вызывающий дальше делает ЯВНЫЙ `BEGIN IMMEDIATE` (begin_tx в service_task_done), sqlite падает `OperationalError: cannot start a transaction within a transaction`. То есть твоя телеметрия роняет ровно ту операцию, которую аудирует. В l26 это крашило закрытие high-risk задач при l3_block_on_high=false.

ПРАВИЛО: для fire-and-forget записи в events из кода, у которого есть только чужой conn, — открывай ОТДЕЛЬНОЕ короткоживущее соединение (sqlite3.connect(db_path, timeout=2), execute, commit, close), путь бери из conn через `PRAGMA database_list` (row[2]; пусто для :memory: → no-op). Так запись не касается транзакции вызывающего. Именно так сделаны emit_supervision_bypass (_common.py) и gate_toggle._record_gate_disable. Symmetric: service-точки с полноценным svc.be.event_add ОБЯЗАНЫ быть в try/except (event_add→_ins не ловит исключений сам), иначе ошибка БД роняет task_done/task_start (fail-open — [[schema-parity-double-gate]] стиль). РЕГРЕСС-ТЕСТ на «после emit BEGIN IMMEDIATE не падает» обязателен. Общий принцип релиза 1.8: телеметрия, роняющая надзор, хуже пропущенной строки.
