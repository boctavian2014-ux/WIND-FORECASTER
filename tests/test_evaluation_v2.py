from services.backtest.engine import evaluate_directional_predictions
from services.backtest.evaluation_v2 import build_strategy_report_v2


def test_build_strategy_report_v2_shapes():
    rows = [
        {
            'label_direction': 1,
            'delta_price': 2.0,
            'predicted_class': 1,
            'prob_down': 0.1,
            'prob_flat': 0.1,
            'prob_up': 0.8,
            'no_trade': False,
        },
        {
            'label_direction': -1,
            'delta_price': -1.0,
            'predicted_class': 0,
            'prob_down': 0.2,
            'prob_flat': 0.6,
            'prob_up': 0.2,
            'no_trade': False,
        },
    ]
    result, evaluated = evaluate_directional_predictions(rows, confidence_threshold=None)
    report = build_strategy_report_v2(result, evaluated)
    assert 'classification_metrics' in report
    assert 'trading_metrics' in report
    assert 'sample_metrics' in report
    assert report['classification_metrics']['confusion_matrix']['1']['1'] == 1
    assert 'per_class' in report['classification_metrics']
