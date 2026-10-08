---
slug: put-v-dinamicheskom-bloke-claude-md-obyazan-byt-svernut-v
title: "Путь в динамическом блоке CLAUDE.md обязан быть свёрнут в ~: файл версионируется"
type: gotcha
tags: []
task: compaction-summary-short-full-history-on-disk
edges: []
---

Смена #277: добавление строки с путём к транскрипту хоста в блок Current State уронило tests/test_publication_lines.py — класс 'a local path carrying the user's name' перестал быть нулём. CLAUDE.md и AGENTS.md отслеживаются git, поэтому полный путь вида C:\Users\<имя>\.claude\projects\... уезжает в историю репозитория вместе с именем пользователя. Свёртка домашнего каталога в '~' сохраняет пользу подсказки (раскрывают и оболочка, и агент) и снимает утечку. ОБЩЕЕ ПРАВИЛО: любая строка, попадающая в динамический блок, проходит ту же границу публикации, что и код, — блок версионируется наравне с остальным файлом.
