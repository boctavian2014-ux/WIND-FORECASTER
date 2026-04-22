from __future__ import annotations

import math
from typing import Any

import numpy as np
from sklearn.metrics import balanced_accuracy_score, precision_recall_fscore_support

from services.backtest.engine import BacktestResult
from services.backtest.metrics import (
    CLASS_LABELS,
    class_counts,
    confusion_matrix_multiclass,
    no_trade_rate,
)

CLASS_LIST = list(CLASS_LABELS)


def _trade_pnls(evaluated_rows: list[dict]) -> list[float]:
    out: list[float] = []
    for r in evaluated_rows:
        if r.get('no_trade'):
            continue
        if int(r.get('predicted_class', 0)) == 0:
            continue
        pnl = float(r.get('trade_pnl') or 0.0)
        out.append(pnl)
    return out


def _profit_factor(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = sum(p for p in pnls if p < 0)
    if losses == 0:
        return None if wins == 0 else float('inf')
    return wins / abs(losses)


def _avg_win_loss(pnls: list[float]) -> tuple[float | None, float | None]:
    pos = [p for p in pnls if p > 0]
    neg = [p for p in pnls if p < 0]
    avg_win = float(np.mean(pos)) if pos else None
    avg_loss = float(np.mean(neg)) if neg else None
    return avg_win, avg_loss


def build_strategy_report_v2(
    result: BacktestResult,
    evaluated_rows: list[dict],
) -> dict[str, Any]:
    """
    Nested dicts aligned with BacktestCompareResponseV2:
    classification_metrics, trading_metrics, sample_metrics.
    """
    n = len(evaluated_rows)
    yt = [int(r['label_direction']) for r in evaluated_rows]
    yp = [int(r['predicted_class']) for r in evaluated_rows]

    cm = confusion_matrix_multiclass(yt, yp) if n else {
        str(a): {str(p): 0 for p in CLASS_LABELS} for a in CLASS_LABELS
    }

    if n:
        acc = float(np.mean(np.asarray(yt) == np.asarray(yp)))
        bal_acc = float(balanced_accuracy_score(yt, yp))
        prec, rec, f1, _ = precision_recall_fscore_support(
            yt,
            yp,
            labels=CLASS_LIST,
            average=None,
            zero_division=0,
        )
        macro_res = precision_recall_fscore_support(
            yt,
            yp,
            labels=CLASS_LIST,
            average='macro',
            zero_division=0,
        )
        macro_p, macro_r, macro_f1 = float(macro_res[0]), float(macro_res[1]), float(macro_res[2])
        per_class: dict[str, dict[str, float]] = {}
        for idx, c in enumerate(CLASS_LIST):
            per_class[str(c)] = {
                'precision': float(prec[idx]),
                'recall': float(rec[idx]),
                'f1': float(f1[idx]),
            }
    else:
        acc = bal_acc = 0.0
        macro_p = macro_r = macro_f1 = 0.0
        per_class = {str(c): {'precision': 0.0, 'recall': 0.0, 'f1': 0.0} for c in CLASS_LIST}

    pnls = _trade_pnls(evaluated_rows)
    trades = len(pnls)
    total_pnl = float(sum(pnls)) if pnls else 0.0
    avg_pnl = total_pnl / trades if trades else 0.0
    avg_win, avg_loss = _avg_win_loss(pnls)
    pf = _profit_factor(pnls)
    if pf is not None and math.isinf(pf):
        pf_out: float | None = None
    else:
        pf_out = pf

    rows_no_trade = sum(1 for r in evaluated_rows if r.get('no_trade'))
    ntr = no_trade_rate(evaluated_rows)
    coverage = trades / n if n else 0.0

    counts_true = class_counts(yt)
    counts_pred = class_counts(yp)

    return {
        'classification_metrics': {
            'accuracy': acc,
            'balanced_accuracy': bal_acc,
            'macro_precision': float(macro_p),
            'macro_recall': float(macro_r),
            'macro_f1': float(macro_f1),
            'per_class': per_class,
            'confusion_matrix': cm,
        },
        'trading_metrics': {
            'trades': int(result.trades),
            'hit_rate': float(result.trade_hit_rate),
            'total_pnl': result.total_pnl,
            'avg_pnl': result.avg_pnl,
            'max_drawdown': result.max_drawdown,
            'profit_factor': pf_out,
            'expectancy': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'no_trade_rate': ntr,
        },
        'sample_metrics': {
            'sample_size': n,
            'rows_no_trade': rows_no_trade,
            'coverage_ratio': coverage,
        },
        'class_distribution_true': class_distribution_normalized(counts_true, n),
        'class_distribution_pred': class_distribution_normalized(counts_pred, n),
        'params_snapshot': {},
    }


def class_distribution_normalized(counts: dict[str, int], total: int) -> dict[str, float]:
    if not total:
        return {str(c): 0.0 for c in CLASS_LABELS}
    return {k: float(v) / float(total) for k, v in counts.items()}
