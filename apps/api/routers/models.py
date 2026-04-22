from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

# Ensure both the project root and apps/api are in sys.path before any local
# imports so that `from deps import ...` and `from schemas.* import ...` resolve
# correctly whether this module is loaded standalone or as apps.api.routers.models.
_API_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_API_ROOT))

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from deps import get_db
from schemas.models import PredictRequest, PredictResponse, TrainBaselineModelRequest, TrainBaselineModelResponse

ROOT = _PROJECT_ROOT

from services.features.dataset_builder import build_dataset
from services.models.logreg_model import LogisticDirectionModel, predict_with_model

router = APIRouter(prefix='/models', tags=['models'])
MODEL_DIR = ROOT / 'artifacts' / 'models'

LABEL_QUERY = text('''
    SELECT zone_id, target_time, label_direction, delta_price
    FROM labels_15m
    WHERE zone_id = :zone_id
      AND target_time BETWEEN :start_ts AND :end_ts
''')

UPSERT_PREDICTIONS = text('''
INSERT INTO model_predictions_15m (
    model_name,
    model_version,
    zone_id,
    forecast_time,
    target_time,
    prob_down,
    prob_flat,
    prob_up,
    predicted_class,
    confidence,
    no_trade
) VALUES (
    :model_name,
    :model_version,
    :zone_id,
    :forecast_time,
    :target_time,
    :prob_down,
    :prob_flat,
    :prob_up,
    :predicted_class,
    :confidence,
    :no_trade
)
ON CONFLICT (model_name, model_version, zone_id, forecast_time, target_time)
DO UPDATE SET
    prob_down = EXCLUDED.prob_down,
    prob_flat = EXCLUDED.prob_flat,
    prob_up = EXCLUDED.prob_up,
    predicted_class = EXCLUDED.predicted_class,
    confidence = EXCLUDED.confidence,
    no_trade = EXCLUDED.no_trade
''')


def _training_frame(db: Session, zone_id: str, start_ts, end_ts) -> pd.DataFrame:
    dataset_rows = build_dataset(db=db, zone_id=zone_id, start_ts=start_ts, end_ts=end_ts)
    label_rows = db.execute(
        LABEL_QUERY,
        {'zone_id': zone_id, 'start_ts': start_ts, 'end_ts': end_ts},
    ).mappings().all()
    labels = {row['target_time']: dict(row) for row in label_rows}
    merged = []
    for row in dataset_rows:
        label_row = labels.get(row['target_time'])
        if label_row is None:
            continue
        merged.append({**row, **label_row})
    return pd.DataFrame(merged)


@router.post('/train-baseline', response_model=TrainBaselineModelResponse)
def train_baseline_model(request: TrainBaselineModelRequest, db: Session = Depends(get_db)):
    df = _training_frame(db, request.zone_id, request.start, request.end)
    if df.empty:
        raise HTTPException(status_code=404, detail='No training rows found. Build datasets and labels first.')

    model_version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    model_path = MODEL_DIR / request.model_name / f'{request.zone_id}_{model_version}.joblib'
    trainer = LogisticDirectionModel()
    try:
        result = trainer.train_with_temporal_split(
            df,
            str(model_path),
            test_holdout_ratio=request.test_holdout_ratio,
            test_start=request.test_start,
            confidence_threshold=request.confidence_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TrainBaselineModelResponse(
        status='ok',
        zone_id=request.zone_id,
        model_name=request.model_name,
        model_version=model_version,
        model_path=result.model_path,
        train_rows=result.train_rows,
        test_rows=result.test_rows,
        train_accuracy=result.train_accuracy,
        test_accuracy=result.test_accuracy,
        test_trade_hit_rate=result.test_trade_hit_rate,
        test_class_distribution=result.test_class_distribution,
        classes=result.classes,
    )


@router.post('/predict', response_model=PredictResponse)
def predict(request: PredictRequest, db: Session = Depends(get_db)):
    model_path = MODEL_DIR / request.model_name / f'{request.zone_id}_{request.model_version}.joblib'
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f'Model file not found: {model_path}')

    df = _training_frame(db, request.zone_id, request.start, request.end)
    if df.empty:
        raise HTTPException(status_code=404, detail='No rows available for prediction.')

    model = LogisticDirectionModel.load(str(model_path))
    scored = predict_with_model(model, df)
    forecast_time = datetime.now(timezone.utc)

    rows = []
    for _, row in scored.iterrows():
        conf = float(row['confidence'])
        rows.append({
            'model_name': request.model_name,
            'model_version': request.model_version,
            'zone_id': request.zone_id,
            'forecast_time': forecast_time,
            'target_time': row['target_time'].to_pydatetime()
            if hasattr(row['target_time'], 'to_pydatetime')
            else row['target_time'],
            'prob_down': float(row['prob_down']),
            'prob_flat': float(row['prob_flat']),
            'prob_up': float(row['prob_up']),
            'predicted_class': int(row['predicted_class']),
            'confidence': conf,
            'no_trade': conf < request.confidence_threshold,
        })

    for payload in rows:
        db.execute(UPSERT_PREDICTIONS, payload)
    db.commit()

    preview = [
        {
            'target_time': str(r['target_time']),
            'predicted_class': r['predicted_class'],
            'prob_down': r['prob_down'],
            'prob_flat': r['prob_flat'],
            'prob_up': r['prob_up'],
            'confidence': r['confidence'],
            'no_trade': r['no_trade'],
        }
        for r in rows[:10]
    ]

    return PredictResponse(
        status='ok',
        zone_id=request.zone_id,
        model_name=request.model_name,
        model_version=request.model_version,
        rows_written=len(rows),
        preview=preview,
    )
