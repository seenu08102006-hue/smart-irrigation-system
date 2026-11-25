-- Smart Irrigation Data Analysis System - SQLite schema
-- Every row comes from a dataset the user uploaded. Nothing is pre-loaded.

CREATE TABLE IF NOT EXISTS datasets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,                 -- original file name
    stored_name TEXT    NOT NULL,                 -- file name on disk (uploads/)
    uploaded_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    size_bytes  INTEGER NOT NULL,
    n_rows      INTEGER NOT NULL,
    n_cols      INTEGER NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded','analyzing','done','error')),
    error       TEXT,
    mapping     TEXT,                             -- JSON: which column is date, temperature, humidity, ...
    results     TEXT,                             -- JSON: cleaning log, statistics, chart data, SVM metrics
    model_file  TEXT                              -- SVM trained on this upload (user_models/)
);

-- Manual predictions made with the SVM of one uploaded dataset
CREATE TABLE IF NOT EXISTS predictions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id          INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    temperature         REAL    NOT NULL,
    humidity            REAL    NOT NULL,
    soil_moisture       REAL    NOT NULL,
    rainfall            REAL    NOT NULL,
    crop_type           TEXT,
    prediction          TEXT    NOT NULL,         -- 'Irrigation Required' / 'No Irrigation Needed'
    irrigation_required INTEGER NOT NULL,         -- 1 / 0
    confidence          REAL    NOT NULL          -- percent
);
CREATE INDEX IF NOT EXISTS idx_pred_dataset ON predictions(dataset_id);
