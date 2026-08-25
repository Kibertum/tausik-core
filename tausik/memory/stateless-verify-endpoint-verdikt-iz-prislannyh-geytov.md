---
slug: stateless-verify-endpoint-verdikt-iz-prislannyh-geytov
title: "Stateless verify-endpoint: вердикт из присланных гейтов + подпись"
type: pattern
tags:
  - ci
  - crypto
  - endpoint
  - http
task: v15-nosdk-verify-endpoint
edges: []
---

verify_endpoint.py (Sift Lite): POST /verify принимает gate-результаты от ЛЮБОГО агента/CI, вердикт = все non-skipped block-гейты прошли И есть хотя бы один реальный PASS (зеркалит run_gates_with_cache), receipt заверяет только ran-гейты. Stateless: БД не трогается, ключ читается из .tausik/keys по project_dir=cwd. Безопасность: bind 127.0.0.1, non-localhost только с --yes-expose (нет auth-слоя), приватный seed никогда не сериализуется. Тестирование: ThreadingHTTPServer port=0 в daemon-треде + http.client — никаких моков HTTP.
