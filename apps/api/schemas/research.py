from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BacktestCompareRequest(BaseModel):
    zone_id: str
    start: datetime
    end: datetime
    confidence_threshold: float = Field(default=0.58, ge=0.0, le=1.0)
    model_name: str = 'logreg_direction'
    model_version: str = Field(..., description='Version string returned by POST /models/train-baseline')


class BacktestStrategyMetricsOut(BaseModel):
    rows: int
    trades: int
    accuracy: float
    trade_hit_rate: float
    avg_pnl: float
    total_pnl: float
    max_drawdown: float
    no_trade_rate: float
    class_counts_true: dict[str, int]
    class_counts_pred: dict[str, int]
    confusion_matrix: dict[str, dict[str, int]]


class SampleAlignmentOut(BaseModel):
    persistence_rows_in_window: int
    model_prediction_rows: int
    aligned_sample_size: int
    persistence_dropped_for_alignment: int


class BacktestCompareResponse(BaseModel):
    status: str
    zone_id: str
    start: datetime
    end: datetime
    confidence_threshold: float
    model_name: str
    model_version: str
    sample: SampleAlignmentOut
    persistence: BacktestStrategyMetricsOut
    persisted_model: BacktestStrategyMetricsOut
    preview_persistence: list[dict]
    preview_model: list[dict]
