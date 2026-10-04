# Аудит публичного среза TAUSIK 1.11.1

Дата: 2026-10-04. Вердикт: **подготовка завершена, выпуск заблокирован**.

## Публичная граница

- Свежий read-only inventory: GitHub — 1 открытая задача (`#206`, автор
  `Yumash`, без milestone); GitLab — 0. Сторонних авторов нет.
- Dry-run committed `HEAD`: 1 622 публикуемых и 3 524 исключённых файла по
  десяти правилам `EXCLUDED_FROM_PUBLIC_SNAPSHOT`.
- Все четыре leak-класса на filtered tree равны нулю: internal host, local user
  path, dev-machine path и host transcript path.
- `changelog.d` не отслеживается и не имеет живых потребителей. Его удаление
  уже зафиксировано в EN/RU changelog; старый механизм не восстанавливается.
- Временный alternate-index срез включил текущие незакоммиченные изменения,
  материализовал 1 731 файл и прошёл public lane: 69 passed, 1 named skip.
  Временное дерево удалено.

## Release inputs

- EN/RU changelog остаётся в `[Unreleased]`: срез версии не выполнялся.
- EN/RU `whats-new-1.11.md` существуют, но публичные ссылки пока указывают на
  `v1.11.0`; перед 1.11.1 их нужно обновить вместе с release body.
- GitHub-атрибуция Codex остаётся
  `Co-authored-by: Codex <codex@openai.com>`.
- Commit, push, tag и release остаются отдельными действиями владельца.

## Оставшиеся блокеры

- Economy acceptance: естественный cohort 89/124/82 response rounds, median
  89 при неизменном пороге не выше 40.
- DER 8,8% пересекает неизменённую цель не выше 5,0%.
- API-equivalent USD остаётся unknown без датированной таблицы цен; недельная
  subscription quota 86% used показывается отдельно.

Ни один tracker, ref, tag или release этим аудитом не изменён. Не запускались
paid/synthetic модели, prompt replay или реконструкция baseline.
