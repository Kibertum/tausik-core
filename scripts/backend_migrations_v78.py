"""Migration v78: structured verification identity and proof policy.

All columns are nullable deliberately. Existing command-only rows remain
legacy audit records and gain no rights by inference. New writers populate all
five columns atomically with the verification run.
"""

MIGRATION_V78: list[str] = [
    "ALTER TABLE verification_runs ADD COLUMN run_trigger TEXT",
    "ALTER TABLE verification_runs ADD COLUMN run_files_json TEXT",
    "ALTER TABLE verification_runs ADD COLUMN gate_signature TEXT",
    "ALTER TABLE verification_runs ADD COLUMN replay_policy TEXT "
    "CHECK(replay_policy IN ('replayable', 'non_replayable'))",
    "ALTER TABLE verification_runs ADD COLUMN presentation_policy TEXT "
    "CHECK(presentation_policy IN ('none', 'single_use'))",
]
