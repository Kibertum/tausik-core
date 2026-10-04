"""Migration v72: bind review evidence to the task and files it reviewed."""

MIGRATION_V72 = [
    "ALTER TABLE reviews ADD COLUMN reviewed_state_fingerprint TEXT",
]
