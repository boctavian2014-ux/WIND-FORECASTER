from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class MLExperiment(Base):
    __tablename__ = 'ml_experiments'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_name: Mapped[str] = mapped_column(Text, nullable=False)
    run_group: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default='completed')
    zone_id: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_name: Mapped[str] = mapped_column(Text, nullable=False, default='persistence')
    evaluation_mode: Mapped[str] = mapped_column(Text, nullable=False, default='same_timestamps')
    prediction_policy: Mapped[str] = mapped_column(Text, nullable=False, default='compare')
    confidence_threshold: Mapped[float | None] = mapped_column(Float)
    price_threshold_value: Mapped[float | None] = mapped_column(Float)
    feature_set_version: Mapped[str | None] = mapped_column(Text)
    dataset_version: Mapped[str | None] = mapped_column(Text)
    label_version: Mapped[str | None] = mapped_column(Text)
    train_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    train_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eval_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eval_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    common_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prediction_rows_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    label_rows_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_after_join: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(Text)
    git_commit_sha: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    params_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    metrics: Mapped[list['MLExperimentMetric']] = relationship(
        back_populates='experiment',
        cascade='all, delete-orphan',
    )
    artifacts: Mapped[list['MLExperimentArtifact']] = relationship(
        back_populates='experiment',
        cascade='all, delete-orphan',
    )


class MLExperimentMetric(Base):
    __tablename__ = 'ml_experiment_metrics'
    __table_args__ = (UniqueConstraint('experiment_id', 'strategy_name', name='uq_experiment_strategy'),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('ml_experiments.id', ondelete='CASCADE'),
        nullable=False,
    )
    strategy_name: Mapped[str] = mapped_column(Text, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage_ratio: Mapped[float | None] = mapped_column(Float)
    rows_no_trade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    no_trade_rate: Mapped[float | None] = mapped_column(Float)
    accuracy: Mapped[float | None] = mapped_column(Float)
    balanced_accuracy: Mapped[float | None] = mapped_column(Float)
    macro_precision: Mapped[float | None] = mapped_column(Float)
    macro_recall: Mapped[float | None] = mapped_column(Float)
    macro_f1: Mapped[float | None] = mapped_column(Float)
    trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trade_hit_rate: Mapped[float | None] = mapped_column(Float)
    total_pnl: Mapped[float | None] = mapped_column(Float)
    avg_pnl: Mapped[float | None] = mapped_column(Float)
    avg_win: Mapped[float | None] = mapped_column(Float)
    avg_loss: Mapped[float | None] = mapped_column(Float)
    profit_factor: Mapped[float | None] = mapped_column(Float)
    expectancy: Mapped[float | None] = mapped_column(Float)
    max_drawdown: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    experiment: Mapped['MLExperiment'] = relationship(back_populates='metrics')


class MLExperimentArtifact(Base):
    __tablename__ = 'ml_experiment_artifacts'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('ml_experiments.id', ondelete='CASCADE'),
        nullable=False,
    )
    strategy_name: Mapped[str | None] = mapped_column(Text)
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    experiment: Mapped['MLExperiment'] = relationship(back_populates='artifacts')
