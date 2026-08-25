---
slug: geyt-check-nad-db-fayly-slep-k-crlf-esli-chitaet-fayl
title: "Гейт «--check» над DB→файлы слеп к CRLF, если читает файл текстовым open()"
type: gotcha
tags:
  - crlf
  - determinism
  - export
  - gate
  - windows
task: state-git-export
edges: []
---

Гейт дрейфа, сравнивающий сгенерированный из БД контент с тем, что лежит на диске (`state export --check`, `renar export --check`, `doc constants --check`), обязан читать диск с `open(path, encoding="utf-8", newline="")`. Дефолтный текстовый режим Python применяет universal-newline трансляцию ПРИ ЧТЕНИИ: CRLF/CR молча схлопывается в LF до сравнения. Значит файл, пересохранённый редактором тиммейта или `git core.autocrlf=true` в CRLF, проходит `--check` зелёным — при том что закоммиченные байты не LF-only. Это ровно та тихая байтовая нерепрезентативность, которую гейт и должен ловить: контракт требует LF «в том числе на Windows», а universal-newline read делает нарушение невидимым. Симметрично записи: пишем с `newline="\n"`, читаем для сравнения с `newline=""`. Поймано адверсариальным ревью state-git-export (репро: записать b'a\r\nb\r\n', прочитать тем же open() → '\r' исчез). См. [[слаги-decisions-memory-translit]] по общей теме детерминизма проекции.
