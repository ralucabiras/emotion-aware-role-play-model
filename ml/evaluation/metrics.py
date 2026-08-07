"""Metrics shared by training and standalone evaluation."""

from itertools import pairwise

import numpy as np


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    values = np.exp(shifted)
    return values / values.sum(axis=1, keepdims=True)


def negative_log_likelihood(logits: np.ndarray, labels: np.ndarray, temperature: float = 1.0) -> float:
    scaled = logits / temperature
    shifted = scaled - scaled.max(axis=1, keepdims=True)
    log_normalizer = np.log(np.exp(shifted).sum(axis=1))
    return float(np.mean(log_normalizer - shifted[np.arange(len(labels)), labels]))


def fit_temperature(logits: np.ndarray, labels: np.ndarray, iterations: int = 80) -> float:
    """Fit a positive scalar temperature on validation logits only."""
    if len(logits) != len(labels) or not len(labels):
        raise ValueError("Temperature fitting requires equally sized, non-empty logits and labels")
    lower, upper = -3.0, 3.0
    ratio = (5**0.5 - 1) / 2
    left = upper - ratio * (upper - lower)
    right = lower + ratio * (upper - lower)
    left_loss = negative_log_likelihood(logits, labels, float(np.exp(left)))
    right_loss = negative_log_likelihood(logits, labels, float(np.exp(right)))
    for _ in range(iterations):
        if left_loss < right_loss:
            upper, right, right_loss = right, left, left_loss
            left = upper - ratio * (upper - lower)
            left_loss = negative_log_likelihood(logits, labels, float(np.exp(left)))
        else:
            lower, left, left_loss = left, right, right_loss
            right = lower + ratio * (upper - lower)
            right_loss = negative_log_likelihood(logits, labels, float(np.exp(right)))
    return float(np.exp((lower + upper) / 2))


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
    from sklearn.metrics import accuracy_score, f1_score

    probabilities = softmax(logits)
    predictions = probabilities.argmax(axis=1)
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_f1": float(f1_score(labels, predictions, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(labels, predictions, average="weighted", zero_division=0)),
        "ece": expected_calibration_error(probabilities, labels),
    }


def per_class_metrics(labels: np.ndarray, predictions: np.ndarray, label_names: list[str]) -> dict:
    from sklearn.metrics import precision_recall_fscore_support

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
