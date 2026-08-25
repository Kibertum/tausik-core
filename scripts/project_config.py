"""TAUSIK config loader — find .tausik/ dir, load/save config, gates config.

Service creation (`get_service`) lives in `service_factory`, and the session /
context-tier / LLM-pricing constants live in `tausik_constants` (re-exported below
for back-compat). Keeping the DB imports out of here means importing the config
loader no longer drags the whole database layer (project-config-god-module-split).
"""

from __future__ import annotations

import json
import logging
import os

# Leaf constants + pure config-value helpers moved to tausik_constants
# (project-config-god-module-split); re-exported so `from project_config import X`
# call sites (MCP handlers, service_session, project_cli, cost_pricing, bootstrap,
# tests) are unchanged.
from tausik_constants import (  # noqa: F401
    CONTEXT_TIER_VALUES,
    DEFAULT_CONTEXT_TIER,
    DEFAULT_SESSION_CAPACITY_CALLS,
    DEFAULT_SESSION_IDLE_THRESHOLD_MINUTES,
    DEFAULT_SESSION_MAX_MINUTES,
    DEFAULT_SESSION_WARN_THRESHOLD_MINUTES,
    lookup_llm_usd_per_million_tokens,
    normalize_llm_pricing_config,
    resolve_context_tier,
)

logger = logging.getLogger(__name__)

# Data lives in .tausik/ (IDE-agnostic)
TAUSIK_DIR = ".tausik"
DB_NAME = "tausik.db"
CONFIG_NAME = "config.json"

# --- Gate defaults ---

# Custom-gate command security lives in `gate_command_policy` (split out at the
# 400-line cap). Re-exported here because callers and tests import it from this
# module.
from gate_command_policy import (  # noqa: E402,F401
    ALLOWED_GATE_EXECUTABLES,
    VALID_GATE_SEVERITIES,
    VALID_GATE_TRIGGERS,
    _validate_custom_gate,
    validate_default_gate_command,
)

# Gate enable/disable lives in `gate_toggle` (split out at the same 400-line cap).
# Re-exported because these names have consumers that reach them through THIS
# module, verified by AST scan rather than assumed: `project_service` imports
# `set_gate_enabled` from here, and `tests/test_config_trust.py` reaches both
# `set_gate_enabled` and `GATE_NAME_RE` as attributes of it.
from gate_toggle import GATE_NAME_RE, set_gate_enabled  # noqa: E402,F401


def is_task_next_model_hint_enabled(cfg: dict | None = None) -> bool:
    """Whether to append non-blocking Claude model hints to ``task next`` / ``hud``.

    Opt-in via root ``.tausik/config.json``::

        "task_next": { "model_hint": true }

    Missing ``task_next``, wrong type, or ``model_hint: false`` → ``False`` (unchanged behavior).
    """
    if cfg is None:
        cfg = load_config()
    tn = cfg.get("task_next")
    if not isinstance(tn, dict):
        return False
    return bool(tn.get("model_hint"))


def is_task_start_model_banner_enabled(cfg: dict | None = None) -> bool:
    """Whether ``task start`` prints the model recommendation banner.

    Default: True (v1.4 polish). Opt-out for headless/CI runs via root
    ``.tausik/config.json``::

        "task_start": { "model_banner": false }

    Missing ``task_start`` key or wrong type → True (default-on). Explicit
    ``false`` disables. Any other truthy value enables.
    """
    if cfg is None:
        cfg = load_config()
    ts = cfg.get("task_start")
    if not isinstance(ts, dict):
        return True
    flag = ts.get("model_banner")
    if flag is False:
        return False
    return True


from default_gates import DEFAULT_GATES  # noqa: E402
from gate_registry import apply_post_scope_enabled  # noqa: E402


def _build_stack_gate_map() -> dict[str, list[str]]:
    """Build mapping: stack -> list of gates to auto-enable."""
    result: dict[str, list[str]] = {}
    for gate_name, gate_cfg in DEFAULT_GATES.items():
        for stack in gate_cfg.get("stacks", []):
            result.setdefault(stack, []).append(gate_name)
    return result


STACK_GATE_MAP: dict[str, list[str]] = _build_stack_gate_map()


def auto_enable_gates_for_stacks(cfg: dict, stacks: list[str]) -> list[str]:
    """Auto-enable gates for detected stacks. Returns list of newly enabled gate names.

    Only enables gates that are not already explicitly configured by the user.
    Writes changes to config under "gates" key.
    """
    user_gates = cfg.setdefault("gates", {})
    newly_enabled: list[str] = []
    for stack in stacks:
        for gate_name in STACK_GATE_MAP.get(stack, []):
            # Skip if user already configured this gate explicitly
            if gate_name in user_gates:
                continue
            user_gates[gate_name] = {"enabled": True}
            newly_enabled.append(gate_name)
    return list(dict.fromkeys(newly_enabled))  # deduplicate preserving order


def home_tier_dir() -> str:
    """`~/.tausik` — место, где живёт ПОЛЬЗОВАТЕЛЬСКИЙ ТИР, а не проект.

    Считается от домашнего каталога НАПРЯМУЮ, а не спрашивается у
    `config_trust.user_config_path`, хотя тот и отвечает на похожий вопрос.
    Разница существенна: `$TAUSIK_USER_CONFIG` переносит ФАЙЛ конфигурации
    (этим пользуется изоляция тестов, `conftest._isolated_config_trust_tiers`),
    но не переносит ДОМАШНИЙ КАТАЛОГ. Здесь спрашивают именно про каталог, с
    которым сталкивается восходящий поиск, и вывод его из переопределяемого
    пути делал запрет пустым ровно там, где переопределение задано.

    Первая версия этой правки выводила каталог из `user_config_path()` ради
    единственного источника истины и была отвергнута прогоном: под pytest
    переопределение уводило тир на выброшенный путь, дом снова становился
    «проектом», и шесть тестов оставались красными.
    """
    return os.path.join(os.path.expanduser("~"), TAUSIK_DIR)


def find_tausik_dir() -> str:
    """Найти каталог `.tausik/` подъёмом от cwd. Переопределение: `TAUSIK_DIR`.

    ПОЛЬЗОВАТЕЛЬСКИЙ ТИР ЗА ПРОЕКТ НЕ ВЫДАЁТСЯ. `config_trust` намеренно кладёт
    пользовательскую конфигурацию по той же раскладке `.tausik/config.json`, но
    в домашнем каталоге; отличить её от проекта подъём не умел. На Windows любой
    временный каталог лежит под `C:\\Users\\<user>`, так что подъём доходил до
    дома всегда — и команда, запущенная где угодно, молча цеплялась к тиру
    конфигурации: `status` показывал пустую сводку вместо «проекта здесь нет»,
    а `init` рапортовал об успехе, ничего не создав.

    Граница проводится по РАВЕНСТВУ каталогу тира, а не по вхождению в дом:
    настоящий проект внутри домашнего каталога (`~/work/proj/.tausik`) обязан
    находиться по-прежнему. Запрет относится к УГАДЫВАНИЮ, а не к выбору —
    явный `TAUSIK_DIR`, указывающий хоть на сам тир, остаётся решением
    пользователя и обрабатывается выше по функции.

    Сравнение идёт по `realpath`, а не по написанию. Вопрос здесь — ТОЖДЕСТВО
    каталога, а не форма пути (ср. конвенцию #378, где предикат о форме читает
    именно написание). На Windows подъём приходит от `TMP`, записанного коротким
    именем 8.3, и кандидат выглядит как `C:\\Users\\DEVELO~1\\.tausik`, тогда как
    `expanduser` отдаёт длинное `C:\\Users\\developer`. Строки не совпадают,
    каталог — тот же самый, и сравнение написаний пропускало тир насквозь.

    ПОДЪЁМ ОСТАНАВЛИВАЕТСЯ НА ДОМЕ. Дом — граница владения: выше него лежат
    каталоги, общие для всех учётных записей, и `.tausik`, найденный там, к
    работающему пользователю отношения не имеет. Одного запрета на сам тир мало:
    без остановки подъём просто перешагивал дом и усыновлял первое, что найдёт
    выше. Дом ПРОВЕРЯЕТСЯ (проект может лежать прямо в нём) и лишь затем
    становится последней ступенью.

    Когда проекта нет, возвращается НЕСУЩЕСТВУЮЩИЙ `cwd/.tausik`: это ответ на
    вопрос «где проект БЫЛ БЫ», и вызывающие, которым нужен существующий,
    проверяют `os.path.isdir` (см. `knowledge_write._project_handle`).
    """
    override = os.environ.get("TAUSIK_DIR")
    if override:
        return override
    try:
        home = os.path.normcase(os.path.realpath(os.path.expanduser("~")))
        forbidden = os.path.normcase(os.path.realpath(home_tier_dir()))
    except Exception:  # noqa: BLE001 — недоступный дом не должен ломать поиск проекта
        home, forbidden = "", ""
    d = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(d, TAUSIK_DIR)
        if os.path.isdir(candidate) and os.path.normcase(os.path.realpath(candidate)) != forbidden:
            return candidate
        if home and os.path.normcase(os.path.realpath(d)) == home:
            break  # дом проверен; выше него владения пользователя кончаются
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    # Default to cwd
    return os.path.join(os.getcwd(), TAUSIK_DIR)


def get_db_path() -> str:
    return os.path.join(find_tausik_dir(), DB_NAME)


# Единственная команда, которой позволено СОЗДАТЬ проект. Всем остальным
# несуществующий каталог — повод отказать, а не повод развернуть пустую базу.
COMMANDS_THAT_MAY_CREATE_A_PROJECT = frozenset({"init"})


def project_missing_message(handle: str) -> str:
    """Текст отказа для команды, запущенной вне проекта."""
    return (
        f"Здесь нет проекта TAUSIK: искали {handle} и не нашли, поднимаясь от "
        f"текущего каталога {os.getcwd()}.\n"
        "Ничего не создано и не прочитано. Пустая сводка была бы неотличима от "
        "сводки настоящего пустого проекта, а созданный на ходу каталог — от "
        "того, что вы завели сами.\n"
        "Зайдите в каталог проекта, выполните `tausik init` здесь, либо укажите "
        "проект явно через TAUSIK_DIR."
    )


def assert_project_exists(command: str) -> None:
    """Отказать, если команда не `init`, а проекта нет.

    `SQLiteBackend.__init__` создаёт каталог и разворачивает схему по факту
    подключения — для `init` это верно, для всех остальных это означало вот что:
    `tausik status`, набранный в произвольном каталоге, МОЛЧА заводил там
    `.tausik/tausik.db` и печатал «Tasks: 0/0 done». Отказ не отличался от
    честного ответа, а побочный эффект оставался на диске.

    Проверка стоит ЗДЕСЬ, а не в бэкенде: бэкенд — механизм, и создание ему
    нужно. Решение о том, позволено ли создавать, принадлежит уровню команды.
    """
    if command in COMMANDS_THAT_MAY_CREATE_A_PROJECT:
        return
    handle = find_tausik_dir()
    if os.path.isdir(handle):
        return
    from tausik_utils import ServiceError

    raise ServiceError(project_missing_message(handle))


def get_config_path(tausik_dir: str | None = None) -> str:
    """Path to ``config.json`` inside *tausik_dir*, or the ambient project's.

    ``tausik_dir`` exists because "the project" is not always the one the
    process happens to stand in. A caller that already holds a project handle
    (an MCP `ProjectService`, a test fixture on ``tmp_path``) must be able to
    say which project it means; resolving from the cwd instead made a call
    declared project-scoped execute globally — see
    `mcp-gate-toggle-mutates-real-project-config`. Omitted → unchanged
    `find_tausik_dir` behavior.
    """
    return os.path.join(tausik_dir or find_tausik_dir(), CONFIG_NAME)


def load_project_config(tausik_dir: str | None = None) -> dict:
    """Raw ``.tausik/config.json`` — the project tier alone, no trusted layers.

    This is what config *writers* must read: `save_config` persists whatever it
    is handed, so round-tripping the effective config (`load_config`) would
    copy the user's and the operator's settings into the repository file.
    Readers want `load_config` instead.
    """
    path = get_config_path(tausik_dir)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    logging.getLogger("tausik.config").warning(
                        "Config root must be an object (%s)", path
                    )
                    return {}
                return normalize_llm_pricing_config(data)
        except (json.JSONDecodeError, OSError) as e:
            logging.getLogger("tausik.config").warning(
                "Config corrupted (%s): %s — using defaults", path, e
            )
    return {}


def load_config_with_rejections(tausik_dir: str | None = None) -> tuple[dict, list]:
    """Effective config plus the guarded keys the project tier tried to weaken.

    Layers merge project < user < managed; on top of that a project-tier value
    for a guarded key applies only if it is at least as strict as what the
    trusted tiers (or the framework default) already establish. See
    `config_trust` for the rule and its honest threat boundary.

    `tausik_dir` scopes ONLY the project tier (mcp-config-read-paths-ignore-
    project-handle): it selects which `.tausik/config.json` the *project* layer
    reads, so a service that speaks for one project describes that project and
    not whichever directory the process happens to stand in. The user and
    managed tiers are read from `~/.tausik` and `$TAUSIK_MANAGED_CONFIG` by
    `config_trust.resolve` and are deliberately NOT reparameterised — they are
    per-machine, not per-project, so making them follow the project directory
    would be a new defect, not a fix. `None` keeps the ambient-project behaviour
    every CLI call relies on.
    """
    from config_trust import resolve

    cfg, rejections = resolve(load_project_config(tausik_dir))
    for r in rejections:
        logger.warning("Config trust tier: %s", r.describe())
    return cfg, rejections


def load_config(tausik_dir: str | None = None) -> dict:
    """Effective config for readers. Rejections are logged, not returned —
    use `load_config_with_rejections` when you need to surface them.

    `tausik_dir` selects the project whose config to read (project tier only);
    `None` = ambient project, byte-identical to the pre-parameterisation path.
    """
    return load_config_with_rejections(tausik_dir)[0]


def save_config(cfg: dict, tausik_dir: str | None = None) -> None:
    """Persist config.json atomically: write to .tmp + os.replace.

    Atomicity guards against partial writes if the process is killed mid-write.
    """
    path = get_config_path(tausik_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_gates(cfg: dict | None = None, tausik_dir: str | None = None) -> dict[str, dict]:
    """Load gates config: merge user overrides on top of defaults.

    Returns dict of gate_name -> gate_config.
    User can override any field per gate in config.json under "gates" key.

    `tausik_dir` is consulted ONLY when `cfg` is not supplied — it selects which
    project's config the gate overrides come from (mcp-config-read-paths-ignore-
    project-handle). When the caller already has a `cfg`, the directory is
    irrelevant. `None` = ambient project (unchanged behaviour).
    """
    if cfg is None:
        cfg = load_config(tausik_dir)
    user_gates = cfg.get("gates", {})
    if not isinstance(user_gates, dict):
        logger.warning("Config `gates` must be an object — user overrides ignored")
        user_gates = {}
    merged: dict[str, dict] = {}
    # Start with defaults
    for name, defaults in DEFAULT_GATES.items():
        gate = dict(defaults)
        override = user_gates.get(name)
        if isinstance(override, dict):
            # An override that swaps a built-in gate's command used to skip the
            # allowed-executable check entirely — it only ran for gate names
            # absent from DEFAULT_GATES. `.tausik/config.json` travels with the
            # repo, so that let a cloned project point `ruff.command` at any
            # binary and have the runner execute it. Validate every command an
            # override supplies, built-in or not; on refusal keep the default.
            if "command" in override:
                # Two independent checks: allow-list ("is this binary
                # tolerable at all?"), then identity ("is it still this
                # gate's tool?"). Rationale in gate_command_policy.
                error = _validate_custom_gate(name, override) or validate_default_gate_command(
                    name, override.get("command"), defaults.get("command")
                )
                if error:
                    logger.warning("Ignoring command override: %s", error)
                    override = {k: v for k, v in override.items() if k != "command"}
            gate.update(override)
        elif override is not None:
            logger.warning("Gate '%s' override must be an object — ignored", name)
        merged[name] = gate
    # Add custom user gates (not in defaults) — with security validation
    for name, ucfg in user_gates.items():
        if name not in merged:
            error = _validate_custom_gate(name, ucfg)
            if error:
                logger.warning("Skipping gate: %s", error)
                continue
            merged[name] = ucfg
    # Post-scope gates own legacy config keys — the registry resolves their
    # effective on/off (gate-registry-single-source).
    apply_post_scope_enabled(merged, cfg)
    return merged


def get_gates_for_trigger(
    trigger: str, cfg: dict | None = None, tausik_dir: str | None = None
) -> list[dict]:
    """Return enabled gates matching a specific trigger.

    Each returned dict includes a 'name' key. `tausik_dir` is forwarded to
    `load_gates` only when `cfg` is not supplied — same project-scoping rule.

    Post-scope gates are excluded — their implementations take the QG-2 close
    context, not ``(gate, files)``; `gate_post_scope` runs them.
    """
    all_gates = load_gates(cfg, tausik_dir)
    result = []
    for name, gate in all_gates.items():
        if not gate.get("enabled", True):
            continue
        if gate.get("phase") == "post_scope":
            continue
        triggers = gate.get("trigger", [])
        if trigger in triggers:
            result.append({**gate, "name": name})
    return result
