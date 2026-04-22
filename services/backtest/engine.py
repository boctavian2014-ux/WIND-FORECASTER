from __future__ import annotations

from dataclasses import dataclass

from services.models.baseline import PersistenceBaselineClassifier


@dataclass
class BacktestResult:
    rows: int
    trades: int
    accuracy: float
    trade_hit_rate: float
    avg_pnl: float
    total_pnl: float
    max_drawdown: float


def evaluate_directional_predictions(
    rows: list[dict],
    *,
    confidence_threshold: float | None = None,
) -> tuple[BacktestResult, list[dict]]:
    """
    Backtest on rows that already contain predicted_class and no_trade.

    If confidence_threshold is not None, rows may contain prob_down, prob_flat, prob_up;
    no_trade is then recomputed as max(prob) < threshold (overrides row no_trade).
    """
    evaluated: list[dict] = []
    pnl_curve: list[float] = []
    cumulative = 0.0
    correct = 0
    trades = 0
    trade_hits = 0

    for row in rows:
        pred_class = int(row['predicted_class'])
        no_trade = bool(row['no_trade'])
        if confidence_threshold is not None and all(
            k in row for k in ('prob_down', 'prob_flat', 'prob_up')
        ):
            conf = max(float(row['prob_down']), float(row['prob_flat']), float(row['prob_up']))
            no_trade = conf < confidence_threshold

        actual = row.get('label_direction')
        delta = float(row.get('delta_price') or 0.0)
        pnl = 0.0
        is_correct = False

        if actual is not None and pred_class == int(actual):
            correct += 1
            is_correct = True

        if not no_trade and pred_class != 0:
            trades += 1
            pnl = float(pred_class) * delta
            cumulative += pnl
            if pnl > 0:
                trade_hits += 1
            pnl_curve.append(cumulative)

        evaluated.append({
            **row,
            'predicted_class': pred_class,
            'no_trade': no_trade,
            'trade_pnl': pnl,
            'is_correct': is_correct,
        })

    max_drawdown = 0.0
    peak = float('-inf')
    for value in pnl_curve:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value - peak)

    rows_count = len(rows)
    accuracy = correct / rows_count if rows_count else 0.0
    trade_hit_rate = trade_hits / trades if trades else 0.0
    total_pnl = cumulative
    avg_pnl = total_pnl / trades if trades else 0.0

    return (
        BacktestResult(rows_count, trades, accuracy, trade_hit_rate, avg_pnl, total_pnl, max_drawdown),
        evaluated,
    )


def run_persistence_backtest(
    rows: list[dict],
    confidence_threshold: float = 0.58,
) -> tuple[BacktestResult, list[dict]]:
    """Rows must include return_15m, label_direction, delta_price."""
    model = PersistenceBaselineClassifier()
    augmented: list[dict] = []
    for row in rows:
        pred = model.predict_row(row, confidence_threshold=confidence_threshold)
        augmented.append({
            **row,
            'predicted_class': pred.predicted_class,
            'prob_down': pred.prob_down,
            'prob_flat': pred.prob_flat,
            'prob_up': pred.prob_up,
            'confidence': pred.confidence,
            'no_trade': pred.no_trade,
        })
    return evaluate_directional_predictions(augmented, confidence_threshold=None)


def run_persisted_model_backtest(
    rows: list[dict],
    confidence_threshold: float | None = 0.58,
) -> tuple[BacktestResult, list[dict]]:
    """
    Rows from DB join: label_direction, delta_price, predicted_class, prob_*, no_trade.

    Re-applies confidence_threshold to no_trade when provided (aligned with /models/predict).
    """
    return evaluate_directional_predictions(rows, confidence_threshold=confidence_threshold)


class SimpleDirectionalBacktest:
    """Thin wrapper for backwards compatibility with earlier Sprint 1 code."""

    def __init__(self, confidence_threshold: float = 0.58):
        self.confidence_threshold = confidence_threshold

    def run(self, rows: list[dict]) -> tuple[BacktestResult, list[dict]]:
        return run_persistence_backtest(rows, confidence_threshold=self.confidence_threshold)
