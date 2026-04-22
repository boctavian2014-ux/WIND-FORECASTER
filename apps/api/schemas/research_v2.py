from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class BacktestCompareRequestV2(BaseModel):
    zone_id: str
    start: datetime
    end: datetime
    model_name: str
    model_version: str
    confidence_threshold: float = Field(default=0.58, gt=0.0, lt=1.0)
    price_threshold_value: float | None = None
    evaluation_mode: Literal['same_timestamps', 'full_period'] = 'same_timestamps'
    prediction_policy: Literal['compare', 'persisted_only', 'persistence_only'] = 'compare'
    baseline_name: str = 'persistence'
    feature_set_version: str | None = None
    dataset_version: str | None = None
    label_version: str | None = None
    source_filters: dict[str, Any] | None = None
    created_by: str | None = None
    git_commit_sha: str | None = None
    notes: str | None = None
    tags: dict[str, Any] = Field(default_factory=dict)
    experiment_name: str | None = None
    persist_experiment: bool = True


class ClassificationMetricsV2(BaseModel):
    accuracy: float
    balanced_accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    per_class: dict[str, dict[str, float]]
    confusion_matrix: dict[str, dict[str, int]]
    class_distribution_true: dict[str, float] = Field(default_factory=dict)
    class_distribution_pred: dict[str, float] = Field(default_factory=dict)


class TradingMetricsV2(BaseModel):
    trades: int
    hit_rate: float
    total_pnl: float
    avg_pnl: float
    max_drawdown: float
    profit_factor: float | None = None
    expectancy: float
    avg_win: float | None = None
    avg_loss: float | None = None
    no_trade_rate: float


class SampleMetricsV2(BaseModel):
    sample_size: int
    rows_no_trade: int
    coverage_ratio: float


class StrategyBlockV2(BaseModel):
    classification_metrics: ClassificationMetricsV2
    trading_metrics: TradingMetricsV2
    sample_metrics: SampleMetricsV2


class ExperimentSummaryV2(BaseModel):
    experiment_id: str | None = None
    experiment_name: str
    zone_id: str
    model_name: str
    model_version: str
    evaluation_mode: str
    prediction_policy: str
    common_sample_size: int
    prediction_rows_found: int
    label_rows_found: int
    rows_after_join: int
    git_commit_sha: str | None = None


class BacktestCompareResponseV2(BaseModel):
    status: str
    experiment: ExperimentSummaryV2
    persistence: StrategyBlockV2 | None = None
    persisted_model: StrategyBlockV2 | None = None
    previews: dict[str, list[dict]] = Field(default_factory=dict)
