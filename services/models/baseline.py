from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BaselinePrediction:
    predicted_class: int
    prob_down: float
    prob_flat: float
    prob_up: float
    confidence: float
    no_trade: bool


class PersistenceBaselineClassifier:
    def predict_row(self, row: dict, confidence_threshold: float = 0.58) -> BaselinePrediction:
        signal = row.get('return_15m')
        if signal is None:
            return BaselinePrediction(0, 0.2, 0.6, 0.2, 0.6, True)
        if signal > 0:
            probs = {'down': 0.15, 'flat': 0.2, 'up': 0.65}
            predicted = 1
        elif signal < 0:
            probs = {'down': 0.65, 'flat': 0.2, 'up': 0.15}
            predicted = -1
        else:
            probs = {'down': 0.2, 'flat': 0.6, 'up': 0.2}
            predicted = 0
        confidence = max(probs.values())
        return BaselinePrediction(
            predicted,
            probs['down'],
            probs['flat'],
            probs['up'],
            confidence,
            confidence < confidence_threshold,
        )
