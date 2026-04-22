from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.backtest.engine import run_persistence_backtest, run_persisted_model_backtest
from services.backtest.evaluation_v2 import build_strategy_report_v2
from services.experiments.git_info import try_git_commit_sha
from services.experiments.persist_v2 import persist_compare_v2

LABEL_COUNT_QUERY = text('''
SELECT COUNT(*) AS c
FROM labels_15m l
WHERE l.zone_id = :zone_id
  AND l.target_time BETWEEN :start_ts AND :end_ts
  AND (NOT CAST(:has_label_version AS BOOLEAN) OR l.label_version = :label_version)
''')

PERSISTENCE_ROW_QUERY_V2 = text('''
WITH ordered AS (
    SELECT
        delivery_start AS target_time,
        price,
        LAG(price, 1) OVER (PARTITION BY zone_id ORDER BY delivery_start) AS prev_price
    FROM intraday_prices_15m
    WHERE zone_id = :zone_id
      AND delivery_start BETWEEN :start_ts AND :end_ts
)
SELECT
    l.target_time,
    l.label_direction,
    l.delta_price,
    CASE
        WHEN o.prev_price IS NULL THEN NULL
        ELSE (o.price - o.prev_price)
    END AS return_15m
FROM labels_15m l
JOIN ordered o ON o.target_time = l.target_time
WHERE l.zone_id = :zone_id
  AND l.target_time BETWEEN :start_ts AND :end_ts
  AND (NOT CAST(:has_label_version AS BOOLEAN) OR l.label_version = :label_version)
ORDER BY l.target_time
''')

PERSISTED_MODEL_ROW_QUERY_V2 = text('''
SELECT DISTINCT ON (mp.target_time)
    mp.target_time,
    l.label_direction,
    l.delta_price,
    mp.predicted_class,
    mp.prob_down,
    mp.prob_flat,
    mp.prob_up,
    mp.confidence,
    mp.no_trade
FROM model_predictions_15m mp
INNER JOIN labels_15m l
    ON l.zone_id = mp.zone_id AND l.target_time = mp.target_time
WHERE mp.zone_id = :zone_id
  AND mp.model_name = :model_name
  AND mp.model_version = :model_version
  AND l.target_time BETWEEN :start_ts AND :end_ts
  AND (NOT CAST(:has_label_version AS BOOLEAN) OR l.label_version = :label_version)
ORDER BY mp.target_time, mp.forecast_time DESC
''')


def _label_params(zone_id: str, start_ts, end_ts, label_version: str | None) -> dict[str, Any]:
    return {
        'zone_id': zone_id,
        'start_ts': start_ts,
        'end_ts': end_ts,
        'has_label_version': label_version is not None,
        'label_version': label_version,
    }


def _preview_rows(eval_rows: list[dict], limit: int = 8) -> list[dict]:
    out: list[dict] = []
    for row in eval_rows[:limit]:
        item: dict[str, Any] = {}
        for k, v in row.items():
            item[k] = v.isoformat() if hasattr(v, 'isoformat') else v
        out.append(item)
    return out


def _strategy_public_block(full_report: dict[str, Any]) -> dict[str, Any]:
    cls = dict(full_report['classification_metrics'])
    cls['class_distribution_true'] = full_report.get('class_distribution_true', {})
    cls['class_distribution_pred'] = full_report.get('class_distribution_pred', {})
    return {
        'classification_metrics': cls,
        'trading_metrics': full_report['trading_metrics'],
        'sample_metrics': full_report['sample_metrics'],
    }


def run_compare_v2(
    db: Session,
    *,
    zone_id: str,
    start: datetime,
    end: datetime,
    model_name: str,
    model_version: str,
    confidence_threshold: float,
    price_threshold_value: float | None,
    evaluation_mode: Literal['same_timestamps', 'full_period'],
    prediction_policy: Literal['compare', 'persisted_only', 'persistence_only'],
    baseline_name: str,
    feature_set_version: str | None,
    dataset_version: str | None,
    label_version: str | None,
    source_filters: dict[str, Any] | None,
    created_by: str | None,
    git_commit_sha: str | None,
    notes: str | None,
    tags: dict[str, Any],
    experiment_name: str | None,
    persist_experiment: bool,
    git_cwd: Path | None,
) -> dict[str, Any]:
    lp = _label_params(zone_id, start, end, label_version)
    label_rows_found = int(db.execute(LABEL_COUNT_QUERY, lp).scalar_one())

    persistence_dicts: list[dict] = []
    if prediction_policy in ('compare', 'persistence_only'):
        persistence_dicts = [dict(r) for r in db.execute(PERSISTENCE_ROW_QUERY_V2, lp).mappings().all()]

    model_dicts: list[dict] = []
    if prediction_policy in ('compare', 'persisted_only'):
        mp = {**lp, 'model_name': model_name, 'model_version': model_version}
        model_dicts = [dict(r) for r in db.execute(PERSISTED_MODEL_ROW_QUERY_V2, mp).mappings().all()]

    prediction_rows_found = len(model_dicts)

    if prediction_policy == 'compare':
        if not persistence_dicts or not model_dicts:
            raise ValueError('compare policy requires both labeled price paths and persisted predictions.')
        if evaluation_mode == 'same_timestamps':
            model_times = {row['target_time'] for row in model_dicts}
            persistence_aligned = [r for r in persistence_dicts if r['target_time'] in model_times]
            model_aligned = model_dicts
            if not persistence_aligned:
                raise ValueError('Could not align persistence rows to persisted model target_time set.')
            rows_after_join = len(persistence_aligned)
            common_sample_size = rows_after_join
        else:
            persistence_aligned = persistence_dicts
            model_aligned = model_dicts
            rows_after_join = 0
            common_sample_size = 0
    elif prediction_policy == 'persistence_only':
        if not persistence_dicts:
            raise ValueError('No labeled rows with prices for persistence backtest in this window.')
        persistence_aligned = persistence_dicts
        model_aligned = []
        rows_after_join = len(persistence_aligned)
        common_sample_size = rows_after_join
    else:  # persisted_only
        if not model_dicts:
            raise ValueError(
                'No rows joined between labels_15m and model_predictions_15m for this model/version/window.',
            )
        persistence_aligned = []
        model_aligned = model_dicts
        rows_after_join = len(model_aligned)
        common_sample_size = rows_after_join

    strategies: dict[str, dict[str, Any]] = {}
    previews: dict[str, list[dict]] = {}

    if prediction_policy in ('compare', 'persistence_only') and persistence_aligned:
        pers_result, pers_eval = run_persistence_backtest(
            persistence_aligned,
            confidence_threshold=confidence_threshold,
        )
        strategies['persistence'] = build_strategy_report_v2(pers_result, pers_eval)
        strategies['persistence']['params_snapshot'] = {
            'confidence_threshold': confidence_threshold,
            'evaluation_mode': evaluation_mode,
            'prediction_policy': prediction_policy,
        }
        previews['persistence'] = _preview_rows(pers_eval)

    if prediction_policy in ('compare', 'persisted_only') and model_aligned:
        model_result, model_eval = run_persisted_model_backtest(
            model_aligned,
            confidence_threshold=confidence_threshold,
        )
        strategies['persisted_model'] = build_strategy_report_v2(model_result, model_eval)
        strategies['persisted_model']['params_snapshot'] = {
            'confidence_threshold': confidence_threshold,
            'evaluation_mode': evaluation_mode,
            'prediction_policy': prediction_policy,
            'model_name': model_name,
            'model_version': model_version,
        }
        previews['persisted_model'] = _preview_rows(model_eval)

    if not strategies:
        raise ValueError('No strategies evaluated; check prediction_policy and data availability.')

    exp_name = experiment_name or f'compare_v2_{zone_id}_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}'
    sha = git_commit_sha or try_git_commit_sha(git_cwd)

    params_json: dict[str, Any] = {
        'evaluation_mode': evaluation_mode,
        'prediction_policy': prediction_policy,
        'price_threshold_value': price_threshold_value,
        'source_filters': source_filters or {},
        'persistence_rows': len(persistence_dicts),
        'model_rows': len(model_dicts),
        'aligned_persistence_rows': len(persistence_aligned),
        'aligned_model_rows': len(model_aligned),
    }

    experiment_id = None
    if persist_experiment:
        experiment_id = persist_compare_v2(
            db,
            experiment_name=exp_name,
            zone_id=zone_id,
            model_name=model_name,
            model_version=model_version,
            baseline_name=baseline_name,
            evaluation_mode=evaluation_mode,
            prediction_policy=prediction_policy,
            confidence_threshold=confidence_threshold,
            price_threshold_value=price_threshold_value,
            feature_set_version=feature_set_version,
            dataset_version=dataset_version,
            label_version=label_version,
            train_window_start=None,
            train_window_end=None,
            eval_window_start=start,
            eval_window_end=end,
            common_sample_size=common_sample_size,
            prediction_rows_found=prediction_rows_found,
            label_rows_found=label_rows_found,
            rows_after_join=rows_after_join,
            created_by=created_by,
            git_commit_sha=sha,
            notes=notes,
            tags=tags or {},
            params_json=params_json,
            strategies=strategies,
            previews=previews,
        )

    experiment_block = {
        'experiment_id': str(experiment_id) if experiment_id else None,
        'experiment_name': exp_name,
        'zone_id': zone_id,
        'model_name': model_name,
        'model_version': model_version,
        'evaluation_mode': evaluation_mode,
        'prediction_policy': prediction_policy,
        'common_sample_size': common_sample_size,
        'prediction_rows_found': prediction_rows_found,
        'label_rows_found': label_rows_found,
        'rows_after_join': rows_after_join,
        'git_commit_sha': sha,
    }

    persistence_public = _strategy_public_block(strategies['persistence']) if 'persistence' in strategies else None
    model_public = _strategy_public_block(strategies['persisted_model']) if 'persisted_model' in strategies else None

    return {
        'status': 'ok',
        'experiment': experiment_block,
        'persistence': persistence_public,
        'persisted_model': model_public,
        'previews': previews,
    }
