---
slug: zakrytyy-spisok-meryay-po-sheme-check-iz-sqlite-master
title: "Закрытый список меряй по СХЕМЕ: CHECK из sqlite_master против объявления плюс строки вне списка — два именованных половинных вердикта"
type: pattern
tags:
  - closed-list
  - renar
  - schema
  - sqlite
task: mandatory-clauses-are-constants-published-as-earned
edges: []
---

SQLite не даёт каталога CHECK-ограничений; единственный носитель — текст DDL в sqlite_master. renar_clause_closed_lists.check_domain(conn, table, column) разбирает `<col> TEXT … CHECK(<col> IN (…))` регулярным выражением и отдаёт кортеж значений или None (нет таблицы/нет CHECK = список открыт — это само по себе красная находка). Подпроверки: «substrate-closed» (CHECK допускает ровно объявленное: лишние и недостающие названы по отдельности) и «rows-inside» (строк вне объявления ноль; таблица не читается = красная, не пропуск). Объявление НЕ дублируй — импортируй SPEC_TYPES/FINDING_CATEGORIES/ADAPT_STATUSES; второй литеральный перечень ловит LIST_RE. Фикстура для мутаций: DROP TABLE + CREATE с изменённым DDL (SQLite не меняет CHECK на месте). Приватный парсер в renar_clause_reactive_adapt._status_domain делегирует общему через ленивый импорт (иначе цикл: closed_lists берёт Subcheck оттуда).
