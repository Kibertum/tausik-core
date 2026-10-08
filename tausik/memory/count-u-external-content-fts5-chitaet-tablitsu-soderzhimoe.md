---
slug: count-u-external-content-fts5-chitaet-tablitsu-soderzhimoe
title: "COUNT(*) у external-content FTS5 читает таблицу-содержимое — тест на равенство числа строк есть тавтология"
type: gotcha
tags: []
task: migration-docstrings-claim-an-unverified-fts-effect
edges: []
---

fts_specs объявлена content='specs', content_rowid='id', то есть EXTERNAL CONTENT. SELECT COUNT(*) FROM fts_specs возвращает счёт таблицы specs, ЧТО БЫ НИ ЛЕЖАЛО В ИНДЕКСЕ, поэтому утверждение "число строк индекса равно числу строк таблицы" не может упасть никогда. Замер на НАМЕРЕННО задвоенном индексе (постинги вставлены повторно после переименования): счётчик 2=2, MATCH возвращает одну строку, собственная integrity-check FTS5 отвечает OK. Задвоенный external-content индекс НЕ НАБЛЮДАЕМ НИ ОДНИМ интерфейсом, которым пользуется продукт.

ПРАКТИКА: прежде чем писать тест о дублях в FTS, прочти ОБЪЯВЛЕНИЕ виртуальной таблицы. Есть content= — счёт и integrity-check бесполезны, индекс трогает только MATCH. Если причина важна, пришпиливай САМО ОБЪЯВЛЕНИЕ: такой тест краснеет, когда таблица перестаёт быть external-content, то есть ровно тогда, когда счёт начал бы что-то значить.
