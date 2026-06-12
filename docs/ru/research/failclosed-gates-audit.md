# Аудит warning-only гейтов → политика fail-closed (v15-failclosed-gate-audit)

Статус: принято (v1.5, эпик v15-evidence-attestation). Принцип заимствован у Walko: предохранитель, который только предупреждает, — это предохранитель, который выключен.

## Единая политика

**Fail-closed по умолчанию.** Гейт, охраняющий инвариант качества, обязан блокировать. Warning-only допустим только по одному из трёх явных оснований:

1. **Adoption-path** — блок наказывал бы за неполное внедрение фичи, а не за риск (нет ключа подписи, pre-миграционные строки, легаси-задачи без новых полей).
2. **High-FP** — проверка эвристическая (ключевые слова, паттерны), и ложный блок дороже пропущенного предупреждения; ремедиация ложного срабатывания неочевидна.
3. **Availability** — отказ инфраструктуры проверки (битая БД, недоступный git) не должен останавливать работу; для shared/CI-сред есть строгий режим.

Каждый hard-гейт обязан иметь: (а) дешёвую ремедиацию в тексте ошибки, (б) явный документированный opt-out (config), (в) тест на негативный сценарий.

## Инвентарь (состояние на v1.5)

| Гейт | Где | Было | Вердикт | Основание |
|---|---|---|---|---|
| QG-0 goal/AC отсутствуют | gate_qg0_check | hard | hard ✓ | — |
| QG-0 AC без негативного сценария | gate_qg0_check | hard | hard ✓ | — |
| QG-0 Rule 6 rollback_plan (явные medium/complex) | gate_qg0_check | hard (v28) | hard ✓ | opt-out нет, unset-complexity = warn (adoption) |
| QG-0 Rule 2 scope (явные medium/complex) | gate_qg0_check | warn → **hard (v1.5)** | hard ✓ | `qg0.scope_hard_gate=false` |
| QG-0 scope_exclude | gate_qg0_check | warn | **keep warn** | High-FP: для многих задач exclude избыточен; scope_paths уже hard |
| QG-0 security-AC (ключевые слова) | gate_qg0_check | warn | **keep warn** | High-FP: keyword-эвристика (SECURITY_KEYWORDS) |
| QG-0 <5/9 intent dimensions | gate_qg0_check | warn | **keep warn** | диагностика полноты, не инвариант |
| QG-2 verify-first (нет свежего verify) | service_gates | hard (v1.4) | hard ✓ | `task_done.auto_verify=true` |
| QG-2 receipt-signature (tamper/substitution) | verify_receipt_check | hard (v1.5) | hard ✓ | NULL receipt / нет ключа = warn (adoption) |
| QG-2 scoped-pytest все skipped | service_verification | hard (synth fail) | hard ✓ | — |
| QG-2 L3 при measured-high risk | risk_l3_trigger | hard (v1.5) | hard ✓ | `risk.l3_block_on_high=false`; thin coverage = pass (High-FP) |
| QG-2 Rule 7 root cause (defect-задачи) | service_task_done | warn → **hard (эта задача)** | hard ✓ | `task_done.root_cause_hard=false`; ремедиация = одна строка task log |
| QG-2 Rule 8 knowledge (complex/defect + --no-knowledge) | service_task_done | refusal (v1.3.4) | hard ✓ | прочие задачи = note (High-FP) |
| QG-2 rollback_plan на done | service_task_done | warn | **keep warn** | Adoption-path: pre-v28 задачи должны закрываться |
| QG-2 AC evidence markers 0/N | service_task_done | warn | **keep warn** | High-FP: парсер формата (✓/AC-N) строг, прозаичное evidence легитимно |
| QG-2 verification checklist | service_task_done | note | **keep warn** | диагностика, дублирует verify-first |
| Hook task_gate (нет активной задачи) | hooks | hard | hard ✓ | fail-open на ошибке БД; `TAUSIK_HOOK_FAIL_SECURE=1` |
| Hook scope_write_gate (вне ACL) | hooks | hard (v1.5) | hard ✓ | задача без ACL = свобода (adoption); fail-open БД + FAIL_SECURE |
| Hook memory_pretool_block | hooks | hard | hard ✓ | bypass-маркер anchored (gotcha #132) |
| Hook secret_scan | hooks | warn | **opt-in strict** | High-FP: паттерны секретов ловят фикстуры; `TAUSIK_SECRET_SCAN_STRICT=1` |
| Hook bash_firewall (опасные команды) | hooks | hard | hard ✓ | — |
| Hook git_push_gate (нет тикета) | hooks | hard | hard ✓ | `tausik push-ok` = ремедиация |
| Session capacity (Rule 9.2) | service_task | hard | hard ✓ | `task start --force` (логируется audit-событием) |

## Изменения этой задачи

- **Rule 7 root cause: warn → hard.** Defect-задача, закрытая без причины, — это ровно тот fail-open, ради которого аудит затевался: дефект «исправлен», а знание о причине потеряно. FP-риск (формулировка без ключевых слов «root cause/причина/из-за…») купирован дешёвой ремедиацией (одна строка `task log "Root cause: ..."`) и opt-out `task_done.root_cause_hard=false`.

## Кандидаты будущего ужесточения (когда уйдёт основание)

- **AC evidence 0/N → hard** после того, как структурированный `--evidence-json` станет основным путём (FP формата исчезнет).
- **secret_scan strict по умолчанию** после введения allowlist для тестовых фикстур.
- **receipt no-key → hard** если/когда `tausik key init` войдёт в bootstrap по умолчанию.
