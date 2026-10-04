"""Migration v71: retain provenance for every benchmark identity field."""

MIGRATION_V71 = [
    """UPDATE benchmark_observations
       SET task_slug=NULL, tausik_version=NULL, attribution_confidence='project'
       WHERE task_slug IS NOT NULL
         AND NOT EXISTS (SELECT 1 FROM tasks WHERE tasks.slug=benchmark_observations.task_slug)""",
    "ALTER TABLE benchmark_observations ADD COLUMN host_basis TEXT",
    "ALTER TABLE benchmark_observations ADD COLUMN host_version_basis TEXT",
    "ALTER TABLE benchmark_observations ADD COLUMN provider_basis TEXT",
    "ALTER TABLE benchmark_observations ADD COLUMN model_basis TEXT",
    "ALTER TABLE benchmark_observations ADD COLUMN reasoning_effort_basis TEXT",
    "ALTER TABLE benchmark_observations ADD COLUMN speed_mode_basis TEXT",
]
