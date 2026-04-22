from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

# Ensure both the project root and apps/api are in sys.path before any local
# imports so that `from deps import ...` and `from schemas.* import ...` resolve
# correctly whether this module is loaded standalone or as apps.api.routers.research.
_API_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_API_ROOT))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from deps import get_db
from schemas.research import (
    BacktestCompareRequest,
    BacktestCompareResponse,
    BacktestStrategyMetricsOut,
    SampleAlignmentOut,
)
from schemas.research_v2 import BacktestCompareRequestV2, BacktestCompareResponseV2

ROOT = _PROJECT_ROOT

from services.backtest.engine import run_persistence_backtest, run_persisted_model_backtest
from services.backtest.metrics import build_strategy_evaluation
from services.research.compare_v2 import run_compare_v2

router = APIRouter(prefix='/research', tags=['research'])

PERSISTENCE_ROW_QUERY = text('''
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
ORDER BY l.target_time
''')

PERSISTED_MODEL_ROW_QUERY = text('''
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
ORDER BY mp.target_time, mp.forecast_time DESC
''')


def _serialize_preview(rows: list[dict], limit: int = 8) -> list[dict]:
    out: list[dict] = []
    for row in rows[:limit]:
        item: dict[str, Any] = {}
        for k, v in row.items():
            if hasattr(v, 'isoformat'):
                item[k] = v.isoformat()
            else:
                item[k] = v
        out.append(item)
    return out


@router.post('/backtest/compare', response_model=BacktestCompareResponse)
def backtest_compare(request: BacktestCompareRequest, db: Session = Depends(get_db)):
    params = {
        'zone_id': request.zone_id,
        'start_ts': request.start,
        'end_ts': request.end,
    }
    persistence_rows = db.execute(PERSISTENCE_ROW_QUERY, params).mappings().all()
    if not persistence_rows:
        raise HTTPException(
            status_code=404,
            detail='No labeled rows with prices for persistence backtest in this window.',
        )
    persistence_dicts = [dict(r) for r in persistence_rows]

    model_params = {
        **params,
        'model_name': request.model_name,
        'model_version': request.model_version,
    }
    model_rows = db.execute(PERSISTED_MODEL_ROW_QUERY, model_params).mappings().all()
    if not model_rows:
        raise HTTPException(
            status_code=404,
            detail=(
                'No rows joined between labels_15m and model_predictions_15m for this '
                'model/version/window. Run POST /models/predict first.'
            ),
        )
    model_dicts = [dict(r) for r in model_rows]
    model_times = {row['target_time'] for row in model_dicts}
    persistence_aligned = [r for r in persistence_dicts if r['target_time'] in model_times]
    if not persistence_aligned:
        raise HTTPException(
            status_code=400,
            detail='Could not align persistence rows to persisted model target_time set.',
        )

    pers_result, pers_eval = run_persistence_backtest(
        persistence_aligned,
        confidence_threshold=request.confidence_threshold,
    )
    model_result, model_eval = run_persisted_model_backtest(
        model_dicts,
        confidence_threshold=request.confidence_threshold,
    )

    sample = SampleAlignmentOut(
        persistence_rows_in_window=len(persistence_dicts),
        model_prediction_rows=len(model_dicts),
        aligned_sample_size=len(persistence_aligned),
        persistence_dropped_for_alignment=len(persistence_dicts) - len(persistence_aligned),
    )

    return BacktestCompareResponse(
        status='ok',
        zone_id=request.zone_id,
        start=request.start,
        end=request.end,
        confidence_threshold=request.confidence_threshold,
        model_name=request.model_name,
        model_version=request.model_version,
        sample=sample,
        persistence=BacktestStrategyMetricsOut.model_validate(
            build_strategy_evaluation(pers_result, pers_eval),
        ),
        persisted_model=BacktestStrategyMetricsOut.model_validate(
            build_strategy_evaluation(model_result, model_eval),
        ),
        preview_persistence=_serialize_preview(pers_eval),
        preview_model=_serialize_preview(model_eval),
    )


@router.post('/backtest/compare-v2', response_model=BacktestCompareResponseV2)
def backtest_compare_v2(request: BacktestCompareRequestV2, db: Session = Depends(get_db)):
    git_cwd = ROOT
    try:
        payload = run_compare_v2(
            db,
            zone_id=request.zone_id,
            start=request.start,
            end=request.end,
            model_name=request.model_name,
            model_version=request.model_version,
            confidence_threshold=request.confidence_threshold,
            price_threshold_value=request.price_threshold_value,
            evaluation_mode=request.evaluation_mode,
            prediction_policy=request.prediction_policy,
            baseline_name=request.baseline_name,
            feature_set_version=request.feature_set_version,
            dataset_version=request.dataset_version,
            label_version=request.label_version,
            source_filters=request.source_filters,
            created_by=request.created_by,
            git_commit_sha=request.git_commit_sha,
            notes=request.notes,
            tags=request.tags,
            experiment_name=request.experiment_name,
            persist_experiment=request.persist_experiment,
            git_cwd=git_cwd,
        )
        return BacktestCompareResponseV2.model_validate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail=(
                'Database error while persisting experiment metrics. '
                'Apply migration db/sql/001_experiment_tracking_v2.sql if tables are missing. '
                f'Original error: {exc}'
            ),
        ) from exc
