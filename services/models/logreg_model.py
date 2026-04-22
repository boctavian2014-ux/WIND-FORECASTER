from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import numpy as np
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    'last_price',
    'return_15m',
    'return_30m',
    'return_60m',
    'spread_vs_dayahead',
    'spread_vs_neighbor_mean',
    'zone_mean_wind_100m',
    'zone_wind_ramp_15m',
    'zone_wind_revision',
    'hour_of_day_sin',
    'hour_of_day_cos',
]


@dataclass
class TrainResult:
    model_path: str
    rows: int
    classes: list[int]
    train_accuracy: float


@dataclass
class TemporalTrainResult:
    model_path: str
    train_rows: int
    test_rows: int
    classes: list[int]
    train_accuracy: float
    test_accuracy: float
    test_trade_hit_rate: float
    test_class_distribution: dict[str, int]


class LogisticDirectionModel:
    def __init__(self):
        numeric_transformer = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
        ])
        preprocessor = ColumnTransformer([
            ('num', numeric_transformer, FEATURE_COLUMNS),
        ])
        classifier = LogisticRegression(
            max_iter=2000,
            solver='lbfgs',
            random_state=42,
        )
        self.pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', classifier),
        ])

    def train(self, df: pd.DataFrame, output_path: str) -> TrainResult:
        train_df = df.dropna(subset=['label_direction']).copy()
        X = train_df[FEATURE_COLUMNS]
        y = train_df['label_direction'].astype(int)
        self.pipeline.fit(X, y)
        preds = self.pipeline.predict(X)
        train_accuracy = float((preds == y).mean())
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, output_path)
        return TrainResult(
            model_path=output_path,
            rows=len(train_df),
            classes=sorted(int(c) for c in self.pipeline.named_steps['classifier'].classes_),
            train_accuracy=train_accuracy,
        )

    def train_with_temporal_split(
        self,
        df: pd.DataFrame,
        output_path: str,
        *,
        test_holdout_ratio: float = 0.2,
        test_start: datetime | None = None,
        confidence_threshold: float = 0.58,
    ) -> TemporalTrainResult:
        """
        Fit on the chronologically earlier segment; evaluate on the later segment.
        test_start (UTC-aware compared to target_time) overrides ratio split when set.
        """
        work = df.dropna(subset=['label_direction']).copy()
        work['target_time'] = pd.to_datetime(work['target_time'], utc=True)
        work = work.sort_values('target_time')
        if work.empty:
            raise ValueError('No labeled rows after dropna.')

        if test_start is not None:
            ts = pd.Timestamp(test_start)
            if ts.tzinfo is None:
                ts = ts.tz_localize('UTC')
            else:
                ts = ts.tz_convert('UTC')
            train_df = work[work['target_time'] < ts]
            test_df = work[work['target_time'] >= ts]
        else:
            ratio = min(max(test_holdout_ratio, 0.05), 0.95)
            split_idx = int(len(work) * (1.0 - ratio))
            split_idx = max(1, min(split_idx, len(work) - 1))
            train_df = work.iloc[:split_idx]
            test_df = work.iloc[split_idx:]

        if train_df.empty or test_df.empty:
            raise ValueError('Temporal split produced an empty train or test set; widen the window or adjust split.')

        X_train, y_train = train_df[FEATURE_COLUMNS], train_df['label_direction'].astype(int)
        X_test, y_test = test_df[FEATURE_COLUMNS], test_df['label_direction'].astype(int)

        self.pipeline.fit(X_train, y_train)

        train_preds = self.pipeline.predict(X_train)
        train_accuracy = float((train_preds == y_train).mean())

        test_preds = self.pipeline.predict(X_test)
        test_accuracy = float((test_preds == y_test).mean())

        probs = self.pipeline.predict_proba(X_test)
        clf_classes = list(self.pipeline.named_steps['classifier'].classes_)
        max_prob = np.max(probs, axis=1)
        y_true_arr = y_test.to_numpy()
        test_preds_arr = np.asarray(test_preds)
        trade_mask = (max_prob >= confidence_threshold) & (test_preds_arr != 0)
        if trade_mask.any():
            test_trade_hit_rate = float((test_preds_arr[trade_mask] == y_true_arr[trade_mask]).mean())
        else:
            test_trade_hit_rate = 0.0

        test_class_distribution = {
            str(int(c)): int((y_test == c).sum()) for c in clf_classes
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, output_path)

        return TemporalTrainResult(
            model_path=output_path,
            train_rows=len(train_df),
            test_rows=len(test_df),
            classes=sorted(int(c) for c in clf_classes),
            train_accuracy=train_accuracy,
            test_accuracy=test_accuracy,
            test_trade_hit_rate=test_trade_hit_rate,
            test_class_distribution=test_class_distribution,
        )

    @staticmethod
    def load(model_path: str):
        return joblib.load(model_path)


def predict_with_model(model, df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURE_COLUMNS].copy()
    classes = [int(c) for c in model.named_steps['classifier'].classes_]
    probs = model.predict_proba(X)
    preds = model.predict(X)
    class_to_idx = {c: idx for idx, c in enumerate(classes)}

    out = df.copy()
    out['predicted_class'] = preds
    n = len(out)
    for cls, col in ((-1, 'prob_down'), (0, 'prob_flat'), (1, 'prob_up')):
        idx = class_to_idx.get(cls)
        out[col] = probs[:, idx] if idx is not None else np.zeros(n, dtype=float)
    out['confidence'] = out[['prob_down', 'prob_flat', 'prob_up']].max(axis=1)
    return out
