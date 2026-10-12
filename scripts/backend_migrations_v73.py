"""Migration v73: sessions.model_source — which source declared the model.

sessions.model_id existed since v14, but WHERE the value came from was thrown
away at insert time. The doctor check (service_doctor_model_source) names
sources in its text, yet for a recorded row it could only re-derive today's
chain — and a mid-session model switch re-points that chain, so the doctor
would name the source of the CURRENT answer as if it had declared the
RECORDED one. Storing the source at session open is the difference between
"which source answered then" and "which source answers now".

Existing rows stay NULL: a model recorded before this column existed has no
honest source to name, and assigning one retroactively would fabricate
provenance — the same rule benchmark_observations followed in v71.
"""

MIGRATION_V73 = [
    "ALTER TABLE sessions ADD COLUMN model_source TEXT",
]
