from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TrainBaselineModelRequest(BaseModel):
    zone_id: str
    start: datetime
    end: datetime
    model_name: str = 'logreg_direction'
    test_holdout_ratio: float = Field(default=0.2, ge=0.05, le=0.95)
    test_start: datetime | None = Field(
        default=None,
        description='If set, rows with target_time < test_start are train; later rows are test (UTC).',
    )
    confidence_threshold: float = Field(
        default=0.58,
        ge=0.0,
        le=1.0,
        description='Same semantics as /models/predict: no_trade when max(prob) < threshold.',
    )


class TrainBaselineModelResponse(BaseModel):
    status: str
    zone_id: str
    model_name: str
    model_version: str
    model_path: str
    train_rows: int
    test_rows: int
    train_accuracy: float
    test_accuracy: float
    test_trade_hit_rate: float
    test_class_distribution: dict[str, int]
    classes: list[int]


class PredictRequest(BaseModel):
    zone_id: str
    start: datetime
    end: datetime
    model_name: str = 'logreg_direction'
    model_version: str
    confidence_threshold: float = Field(default=0.58, ge=0.0, le=1.0)


class PredictResponse(BaseModel):
    status: str
    zone_id: str
    model_name: str
    model_version: str
    rows_written: int
    preview: list[dict]
