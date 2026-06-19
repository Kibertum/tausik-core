# Верификация без SDK: HTTP-endpoint для любого агента и CI

Аттестация TAUSIK без MCP, хуков и SDK. `tausik serve` поднимает stateless
HTTP-endpoint; всё, что умеет JSON по HTTP — GPT-агент, Jenkins, bash-скрипт —
может отправить результаты гейтов и получить **подписанный переносимый
receipt** (`tausik-signed/v1`, ed25519).

## Быстрый старт

```bash
tausik key init          # один раз на проект: ed25519-ключи в .tausik/keys/
tausik serve --port 8765 # bind 127.0.0.1 (auth-слоя нет — только localhost)
```

Не-localhost bind требует явного `--yes-expose` и НЕ рекомендуется: у
endpoint нет аутентификации. Если нужно наружу — ставьте reverse proxy с
авторизацией.

## Endpoints

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/verify` | результаты гейтов → вердикт + подписанный receipt |
| POST | `/receipt/verify` | перепроверка envelope или export-артефакта |
| GET | `/key` | публичный ключ + fingerprint (никогда не seed) |
| GET | `/healthz` | liveness |

### POST /verify

```bash
curl -s http://127.0.0.1:8765/verify -d '{
  "task_slug": "ci-build-42",
  "scope": "standard",
  "git_sha": "0123456789abcdef0123456789abcdef01234567",
  "gates": [
    {"name": "pytest",  "passed": true,  "severity": "block"},
    {"name": "eslint",  "passed": true,  "severity": "warn"},
    {"name": "hadolint","passed": true,  "severity": "warn", "skipped": true}
  ]
}'
```

Ответ: `{"passed": true, "blocking_failed": [], "all_skipped": false,
"envelope": {...}}`.

Семантика вердикта зеркалит локальный пайплайн: каждый non-skipped гейт с
`severity: "block"` обязан пройти, **и** хотя бы один гейт должен был реально
выполниться — all-skipped даёт `passed: false`. Receipt внутри `envelope`
заверяет только реально выполненные гейты.

Ошибки: `400` некорректный вход (в сообщении — какое поле), `503` нет
проектного ключа (`tausik key init`), `404` неизвестный путь.

### POST /receipt/verify

Принимает envelope `tausik-signed/v1` или артефакт `tausik-receipt-export/v1`
(из `tausik receipt export`):

```bash
curl -s http://127.0.0.1:8765/receipt/verify -d @receipt.json
# {"valid": true, "detail": "..."}
```

## Модель доверия

Подпись доказывает **целостность** (receipt не менялся после подписания).
Происхождение проверяется сравнением fingerprint ключа с внеполосным каналом —
вывод `tausik key show`, закреплённая CI-переменная, описание PR. Никогда не
доверяйте fingerprint, встроенному в тот же артефакт, который проверяете.

## Рабочий пример клиента

Исполняемый, проверяемый в CI референс-клиент:
[`tests/test_no_sdk_example.py`](https://github.com/Kibertum/tausik-core/blob/main/tests/test_no_sdk_example.py) — чистый
stdlib `http.client`, без зависимостей. Ядро:

```python
import http.client, json, sys

def submit_gates(host, port, task_slug, gates):
    conn = http.client.HTTPConnection(host, port, timeout=30)
    conn.request("POST", "/verify",
                 body=json.dumps({"task_slug": task_slug, "gates": gates}),
                 headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = json.loads(resp.read())
    if resp.status == 503:
        sys.exit(f"endpoint has no signing key: {data['error']}")
    if resp.status != 200:
        sys.exit(f"verify request rejected ({resp.status}): {data['error']}")
    return data

result = submit_gates("127.0.0.1", 8765, "ci-build-42",
                      [{"name": "pytest", "passed": True, "severity": "block"}])
json.dump(result["envelope"], open("receipt.json", "w"))
sys.exit(0 if result["passed"] else 1)   # красный вердикт валит CI-job
```

## Сниппет GitHub Actions

```yaml
- name: Attest test results with TAUSIK
  run: |
    tausik serve --port 8765 &
    sleep 1
    python ci_verify.py            # клиент выше; exit 1 на красном вердикте
    curl -s http://127.0.0.1:8765/receipt/verify -d @receipt.json
- name: Upload signed receipt
  uses: actions/upload-artifact@v4
  with: { name: tausik-receipt, path: receipt.json }
```
