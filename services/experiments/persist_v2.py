from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

INSERT_EXPERIMENT = text('''
INSERT INTO ml_experiments (
    experiment_name,
    run_group,
    status,
    zone_id,
    model_name,
    model_version,
    baseline_name,
    evaluation_mode,
    prediction_policy,
    confidence_threshold,
    price_threshold_value,
    feature_set_version,
    dataset_version,
    label_version,
    train_window_start,
    train_window_end,
    eval_window_start,
    eval_window_end,
    common_sample_size,
    prediction_rows_found,
    label_rows_found,
    rows_after_join,
    created_by,
    git_commit_sha,
    notes,
    tags,
    params_json
) VALUES (
    :experiment_name,
    :run_group,
    :status,
    :zone_id,
    :model_name,
    :model_version,
    :baseline_name,
    :evaluation_mode,
    :prediction_policy,
    :confidence_threshold,
    :price_threshold_value,
    :feature_set_version,
    :dataset_version,
    :label_version,
    :train_window_start,
    :train_window_end,
    :eval_window_start,
    :eval_window_end,
    :common_sample_size,
    :prediction_rows_found,
    :label_rows_found,
    :rows_after_join,
    :created_by,
    :git_commit_sha,
    :notes,
    CAST(:tags AS JSONB),
    CAST(:params_json AS JSONB)
)
RETURNING id
''')

INSERT_METRIC = text('''
INSERT INTO ml_experiment_metrics (
    experiment_id,
    strategy_name,
    sample_size,
    coverage_ratio,
    rows_no_trade,
    no_trade_rate,
    accuracy,
    balanced_accuracy,
    macro_precision,
    macro_recall,
    macro_f1,
    trades,
    trade_hit_rate,
    total_pnl,
    avg_pnl,
    avg_win,
    avg_loss,
    profit_factor,
    expectancy,
    max_drawdown
) VALUES (
    :experiment_id,
    :strategy_name,
    :sample_size,
    :coverage_ratio,
    :rows_no_trade,
    :no_trade_rate,
    :accuracy,
    :balanced_accuracy,
    :macro_precision,
    :macro_recall,
    :macro_f1,
    :trades,
    :trade_hit_rate,
    :total_pnl,
    :avg_pnl,
    :avg_win,
    :avg_loss,
    :profit_factor,
    :expectancy,
    :max_drawdown
)
''')

INSERT_ARTIFACT = text('''
INSERT INTO ml_experiment_artifacts (experiment_id, strategy_name, artifact_type, artifact_json)
VALUES (
    :experiment_id,
    :strategy_name,
    :artifact_type,
    CAST(:artifact_json AS JSONB)
)
''')


def persist_compare_v2(
    db: Session,
    *,
    experiment_name: str,
    zone_id: str,
    model_name: str,
    model_version: str,
    baseline_name: str,
    evaluation_mode: str,
    prediction_policy: str,
    confidence_threshold: float,
    price_threshold_value: float | None,
    feature_set_version: str | None,
    dataset_version: str | None,
    label_version: str | None,
    train_window_start,
    train_window_end,
    eval_window_start,
    eval_window_end,
    common_sample_size: int,
    prediction_rows_found: int,
    label_rows_found: int,
    rows_after_join: int,
    created_by: str | None,
    git_commit_sha: str | None,
    notes: str | None,
    tags: dict[str, Any],
    params_json: dict[str, Any],
    strategies: dict[str, dict[str, Any]],
    previews: dict[str, list[dict]],
) -> UUID:
    """Persist experiment row, flattened metrics per strategy, and JSON artifacts."""
    exp_row = db.execute(
        INSERT_EXPERIMENT,
        {
            'experiment_name': experiment_name,
            'run_group': None,
            'status': 'completed',
            'zone_id': zone_id,
            'model_name': model_name,
            'model_version': model_version,
            'baseline_name': baseline_name,
            'evaluation_mode': evaluation_mode,
            'prediction_policy': prediction_policy,
            'confidence_threshold': confidence_threshold,
            'price_threshold_value': price_threshold_value,
            'feature_set_version': feature_set_version,
            'dataset_version': dataset_version,
            'label_version': label_version,
            'train_window_start': train_window_start,
            'train_window_end': train_window_end,
            'eval_window_start': eval_window_start,
            'eval_window_end': eval_window_end,
            'common_sample_size': common_sample_size,
            'prediction_rows_found': prediction_rows_found,
            'label_rows_found': label_rows_found,
            'rows_after_join': rows_after_join,
            'created_by': created_by,
            'git_commit_sha': git_commit_sha,
            'notes': notes,
            'tags': json.dumps(tags or {}),
            'params_json': json.dumps(params_json or {}),
        },
    ).first()
    if exp_row is None:
        raise RuntimeError('Failed to insert ml_experiments row.')
    experiment_id = exp_row[0]

    for strategy_name, report in strategies.items():
        cls_m = report['classification_metrics']
        trd_m = report['trading_metrics']
        smp_m = report['sample_metrics']
        db.execute(
            INSERT_METRIC,
            {
                'experiment_id': experiment_id,
                'strategy_name': strategy_name,
                'sample_size': smp_m['sample_size'],
                'coverage_ratio': smp_m['coverage_ratio'],
                'rows_no_trade': smp_m['rows_no_trade'],
                'no_trade_rate': trd_m['no_trade_rate'],
                'accuracy': cls_m['accuracy'],
                'balanced_accuracy': cls_m['balanced_accuracy'],
                'macro_precision': cls_m['macro_precision'],
                'macro_recall': cls_m['macro_recall'],
                'macro_f1': cls_m['macro_f1'],
                'trades': trd_m['trades'],
                'trade_hit_rate': trd_m['hit_rate'],
                'total_pnl': trd_m['total_pnl'],
                'avg_pnl': trd_m['avg_pnl'],
                'avg_win': trd_m['avg_win'],
                'avg_loss': trd_m['avg_loss'],
                'profit_factor': trd_m['profit_factor'],
                'expectancy': trd_m['expectancy'],
                'max_drawdown': trd_m['max_drawdown'],
            },
        )

        artifact_payload = {
            'confusion_matrix': cls_m['confusion_matrix'],
            'per_class': cls_m['per_class'],
            'class_distribution_true': report.get('class_distribution_true', {}),
            'class_distribution_pred': report.get('class_distribution_pred', {}),
            'params_snapshot': report.get('params_snapshot', {}),
        }
        db.execute(
            INSERT_ARTIFACT,
            {
                'experiment_id': experiment_id,
                'strategy_name': strategy_name,
                'artifact_type': 'classification_bundle',
                'artifact_json': json.dumps(artifact_payload),
            },
        )

        preview_rows = previews.get(strategy_name, [])
        if preview_rows:
            db.execute(
                INSERT_ARTIFACT,
                {
                    'experiment_id': experiment_id,
                    'strategy_name': strategy_name,
                    'artifact_type': 'preview_rows',
                    'artifact_json': json.dumps({'rows': preview_rows}),
                },
            )

    db.commit()
    return experiment_id
