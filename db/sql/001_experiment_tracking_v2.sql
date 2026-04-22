-- Experiment tracking + compare v2 (Postgres / TimescaleDB-compatible)
-- Requires: pgcrypto for gen_random_uuid()

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS ml_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_name TEXT NOT NULL,
    run_group TEXT,
    status TEXT NOT NULL DEFAULT 'completed',
    zone_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    baseline_name TEXT NOT NULL DEFAULT 'persistence',
    evaluation_mode TEXT NOT NULL DEFAULT 'same_timestamps',
    prediction_policy TEXT NOT NULL DEFAULT 'compare',
    confidence_threshold DOUBLE PRECISION,
    price_threshold_value DOUBLE PRECISION,
    feature_set_version TEXT,
    dataset_version TEXT,
    label_version TEXT,
    train_window_start TIMESTAMPTZ,
    train_window_end TIMESTAMPTZ,
    eval_window_start TIMESTAMPTZ NOT NULL,
    eval_window_end TIMESTAMPTZ NOT NULL,
    common_sample_size INTEGER NOT NULL DEFAULT 0,
    prediction_rows_found INTEGER NOT NULL DEFAULT 0,
    label_rows_found INTEGER NOT NULL DEFAULT 0,
    rows_after_join INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT,
    git_commit_sha TEXT,
    notes TEXT,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    params_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_ml_experiments_lookup
    ON ml_experiments (zone_id, model_name, model_version, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ml_experiments_eval_window
    ON ml_experiments (eval_window_start, eval_window_end);

CREATE TABLE IF NOT EXISTS ml_experiment_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES ml_experiments(id) ON DELETE CASCADE,
    strategy_name TEXT NOT NULL,
    sample_size INTEGER NOT NULL DEFAULT 0,
    coverage_ratio DOUBLE PRECISION,
    rows_no_trade INTEGER NOT NULL DEFAULT 0,
    no_trade_rate DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    balanced_accuracy DOUBLE PRECISION,
    macro_precision DOUBLE PRECISION,
    macro_recall DOUBLE PRECISION,
    macro_f1 DOUBLE PRECISION,
    trades INTEGER NOT NULL DEFAULT 0,
    trade_hit_rate DOUBLE PRECISION,
    total_pnl DOUBLE PRECISION,
    avg_pnl DOUBLE PRECISION,
    avg_win DOUBLE PRECISION,
    avg_loss DOUBLE PRECISION,
    profit_factor DOUBLE PRECISION,
    expectancy DOUBLE PRECISION,
    max_drawdown DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (experiment_id, strategy_name)
);

CREATE TABLE IF NOT EXISTS ml_experiment_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES ml_experiments(id) ON DELETE CASCADE,
    strategy_name TEXT,
    artifact_type TEXT NOT NULL,
    artifact_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ml_experiment_artifacts_experiment
    ON ml_experiment_artifacts (experiment_id, strategy_name, artifact_type);

ALTER TABLE model_predictions_15m
    ADD COLUMN IF NOT EXISTS dataset_version TEXT,
    ADD COLUMN IF NOT EXISTS feature_set_version TEXT,
    ADD COLUMN IF NOT EXISTS label_version TEXT,
    ADD COLUMN IF NOT EXISTS train_window_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS train_window_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS inference_window_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS inference_window_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS label_threshold_value DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS prediction_rank INTEGER,
    ADD COLUMN IF NOT EXISTS experiment_id UUID,
    ADD COLUMN IF NOT EXISTS metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_model_predictions_lookup_v2
    ON model_predictions_15m (model_name, model_version, zone_id, target_time, forecast_time DESC);

ALTER TABLE labels_15m
    ADD COLUMN IF NOT EXISTS label_version TEXT,
    ADD COLUMN IF NOT EXISTS horizon_minutes INTEGER NOT NULL DEFAULT 15,
    ADD COLUMN IF NOT EXISTS spike_multiple DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS label_source TEXT,
    ADD COLUMN IF NOT EXISTS build_run_id TEXT,
    ADD COLUMN IF NOT EXISTS metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_labels_lookup_v2
    ON labels_15m (zone_id, target_time, label_version);
