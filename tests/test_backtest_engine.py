from services.backtest.engine import (
    evaluate_directional_predictions,
    run_persisted_model_backtest,
    run_persistence_backtest,
)


def test_evaluate_directional_predictions_basic():
    rows = [
        {
            'target_time': 't1',
            'label_direction': 1,
            'delta_price': 10.0,
            'predicted_class': 1,
            'prob_down': 0.1,
            'prob_flat': 0.1,
            'prob_up': 0.8,
            'no_trade': False,
        },
        {
            'target_time': 't2',
            'label_direction': -1,
            'delta_price': -5.0,
            'predicted_class': 1,
            'prob_down': 0.2,
            'prob_flat': 0.2,
            'prob_up': 0.6,
            'no_trade': False,
        },
    ]
    result, evaluated = evaluate_directional_predictions(rows, confidence_threshold=None)
    assert result.rows == 2
    assert result.trades == 2
    assert result.accuracy == 0.5
    assert result.total_pnl == 10.0 + (-5.0)


def test_confidence_threshold_marks_no_trade():
    rows = [
        {
            'label_direction': 1,
            'delta_price': 1.0,
            'predicted_class': 1,
            'prob_down': 0.34,
            'prob_flat': 0.33,
            'prob_up': 0.34,
            'no_trade': False,
        },
    ]
    result, _ = evaluate_directional_predictions(rows, confidence_threshold=0.58)
    assert result.trades == 0


def test_run_persistence_backtest():
    rows = [
        {'return_15m': 1.0, 'label_direction': 1, 'delta_price': 2.0},
        {'return_15m': -1.0, 'label_direction': -1, 'delta_price': 3.0},
    ]
    result, _ = run_persistence_backtest(rows, confidence_threshold=0.58)
    assert result.rows == 2


def test_run_persisted_model_backtest():
    rows = [
        {
            'label_direction': 1,
            'delta_price': 4.0,
            'predicted_class': 1,
            'prob_down': 0.1,
            'prob_flat': 0.1,
            'prob_up': 0.8,
            'no_trade': False,
        },
    ]
    result, _ = run_persisted_model_backtest(rows, confidence_threshold=0.58)
    assert result.trades == 1
    assert result.total_pnl == 4.0
