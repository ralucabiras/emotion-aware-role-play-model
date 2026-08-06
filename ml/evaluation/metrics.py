"""Metrics shared by training and standalone evaluation."""

from itertools import pairwise

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    values = np.exp(shifted)
    return values / values.sum(axis=1, keepdims=True)


def expected_calibration_error(probabilities: np.ndarray, labels: np.ndarray, bins: int = 15) -> float:
    confidences, predictions = probabilities.max(axis=1), probabilities.argmax(axis=1)
    boundaries = np.linspace(0, 1, bins + 1)
    error = 0.0
    for lower, upper in pairwise(boundaries):
        mask = (confidences > lower) & (confidences <= upper)
        if mask.any():
            error += mask.mean() * abs((predictions[mask] == labels[mask]).mean() - confidences[mask].mean())
    return float(error)


def classification_metrics(logits: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    probabilities = softmax(logits)
    predictions = probabilities.argmax(axis=1)
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_f1": float(f1_score(labels, predictions, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(labels, predictions, average="weighted", zero_division=0)),
        "ece": expected_calibration_error(probabilities, labels),
    }


def per_class_metrics(labels: np.ndarray, predictions: np.ndarray, label_names: list[str]) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(
        labels, predictions, labels=range(len(label_names)), zero_division=0
    )
    return {
        name: {
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(f1[index]),
            "support": int(support[index]),
        }
        for index, name in enumerate(label_names)
    }
