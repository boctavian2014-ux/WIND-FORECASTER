import pandas as pd

from services.models.logreg_model import FEATURE_COLUMNS, LogisticDirectionModel


def _synthetic_frame(n: int = 120) -> pd.DataFrame:
    rows = []
    for i in range(n):
        label = -1 if i % 7 == 0 else (1 if i % 5 == 0 else 0)
        rows.append({
            'target_time': pd.Timestamp('2024-01-01', tz='UTC') + pd.Timedelta(minutes=15 * i),
            'label_direction': label,
            'delta_price': 0.1 * label,
            **{c: float((i + hash(c)) % 13) * 0.01 for c in FEATURE_COLUMNS},
        })
    return pd.DataFrame(rows)


def test_train_with_temporal_split(tmp_path):
    df = _synthetic_frame()
    model = LogisticDirectionModel()
    out_path = tmp_path / 'm.joblib'
    result = model.train_with_temporal_split(
        df,
        str(out_path),
        test_holdout_ratio=0.25,
        test_start=None,
        confidence_threshold=0.55,
    )
    assert result.train_rows + result.test_rows == len(df)
    assert 0.0 <= result.test_accuracy <= 1.0
    assert 0.0 <= result.test_trade_hit_rate <= 1.0
    assert set(result.test_class_distribution.keys()).issubset({'-1', '0', '1'})
    assert out_path.exists()
