# OWASP Top 10 — детальные проверки

## A01: Broken Access Control
- [ ] Проверка авторизации на КАЖДОМ endpoint
- [ ] Проверяется ownership ресурсов
- [ ] Нет доверия client-side при принятии решений о доступе
- [ ] CORS настроен явно (не `*`)

## A02: Cryptographic Failures
- [ ] Пароли хешируются через argon2/bcrypt (НЕ MD5/SHA1)
- [ ] Secrets через переменные окружения
- [ ] HTTPS обязателен в production
- [ ] Sensitive данные не попадают в логи

## A03: Injection
- [ ] Только параметризованные SQL-запросы
- [ ] ORM используется корректно
- [ ] Command injection предотвращён
- [ ] textContent вместо innerHTML (XSS)

## A04: Insecure Design
- [ ] Валидация входов на границах системы
- [ ] Реализован rate limiting
- [ ] Безопасный отказ (без утечки информации)

## A05: Security Misconfiguration
- [ ] Debug-режим отключён в production
- [ ] Настроены security headers
- [ ] Дефолтные credentials изменены
- [ ] Сообщения об ошибках не раскрывают внутренности

## A07: Authentication Failures
- [ ] Сильные требования к паролям (12+ символов)
- [ ] Блокировка аккаунта после неудачных попыток
- [ ] Безопасное управление сессиями
- [ ] MFA там, где это уместно

## A08: Data Integrity Failures
- [ ] Зависимости верифицируются (lock-файлы)
- [ ] Нет десериализации недоверенных данных
- [ ] CI/CD pipeline защищён

## A09: Logging Failures
- [ ] События безопасности логируются
- [ ] В логах нет sensitive данных
- [ ] Log injection предотвращён

## A10: SSRF
- [ ] Валидация URL для внешних запросов
- [ ] Allowlist для внешних сервисов
- [ ] Нет доступа к внутренней сети

## Cookie Security

```
httpOnly: true    # No JS access
secure: true      # HTTPS only
sameSite: strict  # CSRF protection
```

## Управление секретами

### Категорически нельзя
- Хардкодить секреты в коде
- Коммитить .env файлы
- Логировать секреты или токены
- Хранить пароли в открытом виде

### Всегда делай
- Используй переменные окружения
- Используй secrets managers (Vault, AWS SM)
- Регулярно ротируй credentials
- Добавляй секреты в .gitignore

## Чек-лист перед деплоем

- [ ] Зависимости проверены на уязвимости
- [ ] Security headers настроены
- [ ] HTTPS enforced
- [ ] Секреты в безопасном хранилище
- [ ] Логирование настроено правильно
- [ ] Debug-режим отключён
