# TODO

## Post-Release
- [ ] Reduce onboarding friction: create a one-line install script (`curl ... | bash` or similar)
- [ ] Add GIF/demo to README (optional but recommended for adoption)
- [ ] Set up GitHub repo Yumash/TAUSIK and verify CI badges work
- [ ] Publish to PyPI (if applicable)
- [ ] Create example project demonstrating TAUSIK workflow
- [ ] Gather community feedback on skill system

## Shared Brain
- [ ] Проработать Outline как альтернативный backend для shared brain (self-hosted, API, FTS из коробки). Сейчас идём на Notion — вернуться к сравнению после MVP (2026-04-22)

## Hooks / Notifications
- [ ] Подключить `notify_on_done` hook (Discord/Slack/Telegram уведомления о `task_done`). Реализация была написана, но удалена в 1.3.6 как orphan. Восстановить из git history (commit до 1.3.6) и зарегистрировать PostToolUse в `bootstrap_generate.py` + опциональный конфиг через `.tausik/config.json` (channel + webhook). Срок: после стабилизации 1.3.x.
