# Codex L3 read-only path (TB-009)

[English](../en/codex-l3-readonly.md) | **Русский**

<!-- doc-map: reader=agent; zone=quality -->

Ограниченное L3 на хосте Codex требует **механически** read-only ревьюера,
который при этом **читает** репозиторий. Продуктовый `red`/`green` нельзя
записывать, если хост этого не умеет — в dogfood так сгорели оба repair-раунда
(`bugs.txt` TB-009).

## Поддерживаемый запуск Codex

```text
codex exec --sandbox read-only --ephemeral
```

Модель — того же семейства, что у автора. `Author model: <id>` из пакета /
поля `delegation` передавайте в `review cohort-record --author-model`.

## Preflight возможности

Объявите поверхность ревьюера в `.tausik/config.json`:

```json
{
  "review": {
    "l3_host": {
      "tools": ["Read", "Grep", "Bash"],
      "read_probe_results": {
        "Get-Content": true,
        "rg": true,
        "cmd /c type": true,
        "Set-Content": false,
        "Out-File": false,
        "Remove-Item": false,
        "New-Item": false
      }
    }
  }
}
```

- Редакторы с записью (`Write`, `Edit`, …) → `L3_HOST_WRITE_CAPABLE`.
- Read-пробы заблокированы при «read-only» sandbox → `L3_READONLY_POLICY_BLOCKS_READS`.
- Если `review.l3_host` задан и оценка красная, `cohort-record` отказывает с
  `review_infrastructure_blocked` и **не** двигает `current_round`.

## Квитанция инфраструктуры (бюджет сохранён)

```text
.tausik/tausik review cohort-infrastructure-blocked <id> \
  --round 1 \
  --packet-digest <digest> \
  --code L3_READONLY_POLICY_BLOCKS_READS \
  --reason "Codex read-only policy blocked Get-Content/rg" \
  --detail "Windows PowerShell"
```

`rounds` остаётся `0/2` (или `1/2` перед round 2). Почините хост, затем
делайте настоящее file review.

## Отрицательный сценарий

Write-capable хост нельзя записать как L3 PASS. Предпочтительна
infrastructure-квитанция, а не выдуманные findings.
