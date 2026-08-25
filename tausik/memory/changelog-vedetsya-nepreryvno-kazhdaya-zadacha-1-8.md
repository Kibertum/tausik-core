---
slug: changelog-vedetsya-nepreryvno-kazhdaya-zadacha-1-8
title: "CHANGELOG ведётся непрерывно: каждая задача 1.8 обновляет [Unreleased] + зеркало ru"
type: convention
tags:
  - changelog
  - discipline
  - release-1.8
task: null
edges: []
---

Для «одного большого 1.8» CHANGELOG пишется ПО ХОДУ, не в конце. Каждая закрываемая задача 1.8 обязана добавить запись в CHANGELOG.md [Unreleased] (стиль репозитория — прозаический абзац на фичу/фикс, а не сухой bullet) и синхронно в зеркало CHANGELOG.ru.md. Требование внесено в acceptance_criteria всех задач 1.8. Причина: релиз копит десятки изменений; собрать changelog постфактум = гарантированно что-то забыть. Финальная doc-swarm задача лишь сверяет и полирует, а не пишет changelog с нуля.
