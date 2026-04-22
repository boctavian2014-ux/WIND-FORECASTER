from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from services.backtest.engine import BacktestResult

CLASS_LABELS = (-1, 0, 1)


def class_counts(values: Iterable[int]) -> dict[str, int]:
    counts = Counter(int(v) for v in values)
    return {str(c): int(counts.get(c, 0)) for c in CLASS_LABELS}


def no_trade_rate(evaluated_rows: list[dict]) -> float:
    n = len(evaluated_rows)
    if not n:
        return 0.0
    return sum(1 for r in evaluated_rows if r.get('no_trade')) / n


def confusion_matrix_multiclass(
    y_true: list[int],
    y_pred: list[int],
    *,
    classes: tuple[int, ...] = CLASS_LABELS,
) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {
        str(a): {str(p): 0 for p in classes} for a in classes
    }
    n = min(len(y_true), len(y_pred))
    for i in range(n):
        yt, yp = int(y_true[i]), int(y_pred[i])
        matrix[str(yt)][str(yp)] += 1
    return matrix


def build_strategy_evaluation(result: BacktestResult, evaluated_rows: list[dict]) -> dict:
    """Returns dict suitable for BacktestStrategyMetricsOut.model_validate."""
    yt = [int(r['label_direction']) for r in evaluated_rows]
    yp = [int(r['predicted_class']) for r in evaluated_rows]
    cm = confusion_matrix_multiclass(yt, yp) if evaluated_rows else {
        str(a): {str(p): 0 for p in CLASS_LABELS} for a in CLASS_LABELS
    }
    return {
        'rows': result.rows,
        'trades': result.trades,
        'accuracy': result.accuracy,
        'trade_hit_rate': result.trade_hit_rate,
        'avg_pnl': result.avg_pnl,
        'total_pnl': result.total_pnl,
        'max_drawdown': result.max_drawdown,
        'no_trade_rate': no_trade_rate(evaluated_rows),
        'class_counts_true': class_counts(yt),
        'class_counts_pred': class_counts(yp),
        'confusion_matrix': cm,
    }
