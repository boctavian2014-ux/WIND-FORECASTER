from services.backtest.engine import evaluate_directional_predictions
from services.backtest.metrics import (
    build_strategy_evaluation,
    class_counts,
    confusion_matrix_multiclass,
    no_trade_rate,
)


def test_confusion_matrix_multiclass():
    yt = [-1, 0, 1, 1]
    yp = [-1, 0, 0, 1]
    cm = confusion_matrix_multiclass(yt, yp)
    assert cm['-1']['-1'] == 1
    assert cm['1']['0'] == 1
    assert cm['1']['1'] == 1


def test_no_trade_rate():
    rows = [{'no_trade': True}, {'no_trade': False}]
    assert no_trade_rate(rows) == 0.5


def test_class_counts():
    assert class_counts([1, 1, 0]) == {'-1': 0, '0': 1, '1': 2}


def test_build_strategy_evaluation():
    rows = [
        {
            'label_direction': 1,
            'delta_price': 1.0,
            'predicted_class': 1,
            'prob_down': 0.1,
            'prob_flat': 0.1,
            'prob_up': 0.8,
            'no_trade': False,
        },
        {
            'label_direction': -1,
            'delta_price': -2.0,
            'predicted_class': 1,
            'prob_down': 0.2,
            'prob_flat': 0.2,
            'prob_up': 0.6,
            'no_trade': True,
        },
    ]
    result, evaluated = evaluate_directional_predictions(rows, confidence_threshold=None)
    payload = build_strategy_evaluation(result, evaluated)
    assert payload['rows'] == 2
    assert payload['no_trade_rate'] == 0.5
    assert payload['confusion_matrix']['1']['1'] == 1
