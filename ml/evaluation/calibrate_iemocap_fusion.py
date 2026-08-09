"""Fit late-fusion parameters on validation rows and evaluate frozen test rows."""

import argparse
import json
from pathlib import Path

import numpy as np

from ml.evaluation.fuse_iemocap_modalities import _classification_summary
from ml.evaluation.metrics import (
    expected_calibration_error,
    fit_temperature,
    negative_log_likelihood,
    softmax,
)


def _rows(path: Path) -> dict[str, dict]:
    return {row["id"]: row for row in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def _matrix(rows: dict[str, dict], ids: list[str], labels: list[str]) -> np.ndarray:
    return np.asarray([[rows[item]["probabilities_calibrated"][label] for label in labels] for item in ids])


def _logits(rows: dict[str, dict], ids: list[str]) -> np.ndarray:
    try:
        return np.asarray([rows[item]["logits"] for item in ids], dtype=float)
    except KeyError as error:
        raise ValueError("Validation rows must contain raw logits for global calibration") from error


def _recover_logits(rows: dict[str, dict], ids: list[str], labels: list[str], fold_temperature: float) -> np.ndarray:
    probabilities = np.clip(_matrix(rows, ids, labels), 1e-12, 1.0)
    return np.log(probabilities) * fold_temperature


def probability_metrics(probabilities: np.ndarray, expected: np.ndarray, bins: int = 10) -> dict:
    selected = np.clip(probabilities[np.arange(len(expected)), expected], 1e-12, 1.0)
    one_hot = np.eye(probabilities.shape[1])[expected]
    confidence = probabilities.max(axis=1)
    predicted = probabilities.argmax(axis=1)
    reliability = []
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        mask = (confidence >= lower) & (confidence < upper if index < bins - 1 else confidence <= upper)
        reliability.append(
            {
                "lower": lower,
                "upper": upper,
                "count": int(mask.sum()),
                "mean_confidence": float(confidence[mask].mean()) if mask.any() else None,
                "accuracy": float((predicted[mask] == expected[mask]).mean()) if mask.any() else None,
            }
        )
    return {
        "nll": float(-np.log(selected).mean()),
        "multiclass_brier": float(np.square(probabilities - one_hot).sum(axis=1).mean()),
        "reliability_bins": reliability,
    }


def fit_parameters(text: np.ndarray, audio: np.ndarray, expected: np.ndarray) -> tuple[float, float, float]:
    """Grid-search weight and fit temperature using validation NLL only."""
    best = None
    for text_weight in np.linspace(0.0, 1.0, 101):
        probabilities = np.clip(text_weight * text + (1.0 - text_weight) * audio, 1e-12, 1.0)
        log_probabilities = np.log(probabilities)
        temperature = fit_temperature(log_probabilities, expected)
        nll = negative_log_likelihood(log_probabilities, expected, temperature)
        candidate = (nll, abs(text_weight - 0.5), float(text_weight), float(temperature))
        if best is None or candidate < best:
            best = candidate
    return best[2], best[3], best[0]


def run(text_dir: Path, audio_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    fold_results = []
    all_expected, all_predicted, all_probabilities = [], [], []
    for fold in range(1, 6):
        text_metrics = json.loads((text_dir / f"fold-{fold}" / "metrics.json").read_text())
        audio_metrics = json.loads((audio_dir / f"fold-{fold}" / "metrics.json").read_text())
        labels = text_metrics["labels"]
        if labels != audio_metrics["labels"]:
            raise ValueError(f"Label order differs in fold {fold}")
        text_validation = _rows(text_dir / f"fold-{fold}" / "validation_predictions.jsonl")
        audio_validation = _rows(audio_dir / f"fold-{fold}" / "validation_predictions.jsonl")
        if text_validation.keys() != audio_validation.keys():
            raise ValueError(f"Validation ids differ in fold {fold}")
        validation_ids = list(text_validation)
        validation_expected = np.asarray([labels.index(text_validation[item]["expected"]) for item in validation_ids])
        weight, temperature, validation_nll = fit_parameters(
            _matrix(text_validation, validation_ids, labels),
            _matrix(audio_validation, validation_ids, labels),
            validation_expected,
        )
        text_test = _rows(text_dir / f"fold-{fold}" / "test_predictions.jsonl")
        audio_test = _rows(audio_dir / f"fold-{fold}" / "test_predictions.jsonl")
        if text_test.keys() != audio_test.keys():
            raise ValueError(f"Test ids differ in fold {fold}")
        test_ids = list(text_test)
        expected_names = [text_test[item]["expected"] for item in test_ids]
        if expected_names != [audio_test[item]["expected"] for item in test_ids]:
            raise ValueError(f"Test labels differ in fold {fold}")
        fused = weight * _matrix(text_test, test_ids, labels) + (1.0 - weight) * _matrix(audio_test, test_ids, labels)
        calibrated = softmax(np.log(np.clip(fused, 1e-12, 1.0)) / temperature)
        predicted_names = [labels[index] for index in calibrated.argmax(axis=1)]
        expected_ids = np.asarray([labels.index(value) for value in expected_names])
        metrics = _classification_summary(expected_names, predicted_names, labels)
        metrics["ece"] = expected_calibration_error(calibrated, expected_ids)
        metrics.update(probability_metrics(calibrated, expected_ids))
        metrics.update({"fold": fold, "text_weight": weight, "temperature": temperature, "validation_nll": validation_nll})
        fold_results.append(metrics)
        fold_dir = output_dir / f"fold-{fold}"
        fold_dir.mkdir(exist_ok=True)
        with (fold_dir / "test_predictions.jsonl").open("w", encoding="utf-8") as handle:
            for item_id, expected, predicted, probability in zip(
                test_ids, expected_names, predicted_names, calibrated, strict=True
            ):
                handle.write(
                    json.dumps(
                        {
                            "id": item_id,
                            "expected": expected,
                            "predicted": predicted,
                            "confidence": float(probability.max()),
                            "probabilities": {
                                label: float(probability[index]) for index, label in enumerate(labels)
                            },
                        }
                    )
                    + "\n"
                )
        all_expected.extend(expected_names)
        all_predicted.extend(predicted_names)
        all_probabilities.extend(calibrated.tolist())
    pooled = _classification_summary(all_expected, all_predicted, labels)
    pooled["ece"] = expected_calibration_error(
        np.asarray(all_probabilities), np.asarray([labels.index(value) for value in all_expected])
    )
    pooled.update(
        probability_metrics(
            np.asarray(all_probabilities),
            np.asarray([labels.index(value) for value in all_expected]),
        )
    )
    result = {
        "experiment": "iemocap_benchmark4_validation_fitted_fusion",
        "method": "per_fold_validation_nll_weight_and_temperature",
        "weight_grid": {"minimum": 0.0, "maximum": 1.0, "step": 0.01},
        "folds": fold_results,
        "pooled": pooled,
    }
    (output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def run_global_oof(text_dir: Path, audio_dir: Path, output_dir: Path) -> dict:
    """Fit one deployable calibrator on pooled out-of-fold validation predictions."""
    output_dir.mkdir(parents=True, exist_ok=True)
    validation_text_logits, validation_audio_logits, validation_expected = [], [], []
    validation_ids_seen: set[str] = set()
    labels = None
    for fold in range(1, 6):
        text_metrics = json.loads((text_dir / f"fold-{fold}" / "metrics.json").read_text())
        audio_metrics = json.loads((audio_dir / f"fold-{fold}" / "metrics.json").read_text())
        if text_metrics["labels"] != audio_metrics["labels"]:
            raise ValueError(f"Label order differs in fold {fold}")
        labels = labels or text_metrics["labels"]
        if labels != text_metrics["labels"]:
            raise ValueError("Label order differs across folds")
        text_rows = _rows(text_dir / f"fold-{fold}" / "validation_predictions.jsonl")
        audio_rows = _rows(audio_dir / f"fold-{fold}" / "validation_predictions.jsonl")
        if text_rows.keys() != audio_rows.keys():
            raise ValueError(f"Validation ids differ in fold {fold}")
        if duplicate := validation_ids_seen & text_rows.keys():
            raise ValueError(f"Validation ids occur in multiple folds: {sorted(duplicate)[:3]}")
        validation_ids_seen.update(text_rows)
        ids = list(text_rows)
        validation_text_logits.extend(_logits(text_rows, ids).tolist())
        validation_audio_logits.extend(_logits(audio_rows, ids).tolist())
        validation_expected.extend(labels.index(text_rows[item]["expected"]) for item in ids)
    if labels is None:
        raise ValueError("No validation predictions found")
    validation_expected_array = np.asarray(validation_expected)
    validation_text_logits_array = np.asarray(validation_text_logits)
    validation_audio_logits_array = np.asarray(validation_audio_logits)
    text_temperature = fit_temperature(validation_text_logits_array, validation_expected_array)
    audio_temperature = fit_temperature(validation_audio_logits_array, validation_expected_array)
    validation_text = softmax(validation_text_logits_array / text_temperature)
    validation_audio = softmax(validation_audio_logits_array / audio_temperature)
    weight, temperature, validation_nll = fit_parameters(
        validation_text, validation_audio, validation_expected_array
    )
    all_expected, all_predicted, all_probabilities = [], [], []
    fold_results = []
    for fold in range(1, 6):
        text_metrics = json.loads((text_dir / f"fold-{fold}" / "metrics.json").read_text())
        audio_metrics = json.loads((audio_dir / f"fold-{fold}" / "metrics.json").read_text())
        text_rows = _rows(text_dir / f"fold-{fold}" / "test_predictions.jsonl")
        audio_rows = _rows(audio_dir / f"fold-{fold}" / "test_predictions.jsonl")
        if text_rows.keys() != audio_rows.keys():
            raise ValueError(f"Test ids differ in fold {fold}")
        ids = list(text_rows)
        expected_names = [text_rows[item]["expected"] for item in ids]
        if expected_names != [audio_rows[item]["expected"] for item in ids]:
            raise ValueError(f"Test labels differ in fold {fold}")
        text_probabilities = softmax(
            _recover_logits(
                text_rows, ids, labels, text_metrics["calibration"]["temperature"]
            )
            / text_temperature
        )
        audio_probabilities = softmax(
            _recover_logits(
                audio_rows, ids, labels, audio_metrics["calibration"]["temperature"]
            )
            / audio_temperature
        )
        fused = weight * text_probabilities + (1.0 - weight) * audio_probabilities
        calibrated = softmax(np.log(np.clip(fused, 1e-12, 1.0)) / temperature)
        predicted_names = [labels[index] for index in calibrated.argmax(axis=1)]
        expected_ids = np.asarray([labels.index(value) for value in expected_names])
        metrics = _classification_summary(expected_names, predicted_names, labels)
        metrics["ece"] = expected_calibration_error(calibrated, expected_ids)
        metrics.update(probability_metrics(calibrated, expected_ids))
        metrics["fold"] = fold
        fold_results.append(metrics)
        fold_dir = output_dir / f"fold-{fold}"
        fold_dir.mkdir(exist_ok=True)
        with (fold_dir / "test_predictions.jsonl").open("w", encoding="utf-8") as handle:
            for item_id, expected, predicted, probability in zip(
                ids, expected_names, predicted_names, calibrated, strict=True
            ):
                handle.write(
                    json.dumps(
                        {
                            "id": item_id,
                            "expected": expected,
                            "predicted": predicted,
                            "confidence": float(probability.max()),
                            "probabilities": {
                                label: float(probability[index]) for index, label in enumerate(labels)
                            },
                        }
                    )
                    + "\n"
                )
        all_expected.extend(expected_names)
        all_predicted.extend(predicted_names)
        all_probabilities.extend(calibrated.tolist())
    expected_ids = np.asarray([labels.index(value) for value in all_expected])
    probabilities = np.asarray(all_probabilities)
    pooled = _classification_summary(all_expected, all_predicted, labels)
    pooled["ece"] = expected_calibration_error(probabilities, expected_ids)
    pooled.update(probability_metrics(probabilities, expected_ids))
    result = {
        "experiment": "iemocap_benchmark4_global_oof_calibrated_fusion",
        "method": "global_weight_and_temperature_fitted_on_pooled_oof_validation_predictions",
        "validation_examples": len(validation_expected),
        "text_temperature": text_temperature,
        "audio_temperature": audio_temperature,
        "text_weight": weight,
        "audio_weight": 1.0 - weight,
        "temperature": temperature,
        "validation_nll": validation_nll,
        "weight_grid": {"minimum": 0.0, "maximum": 1.0, "step": 0.01},
        "folds": fold_results,
        "pooled": pooled,
    }
    (output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-dir", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scope", choices=("per-fold", "global-oof"), default="per-fold")
    args = parser.parse_args()
    function = run_global_oof if args.scope == "global-oof" else run
    print(json.dumps(function(args.text_dir, args.audio_dir, args.output_dir), indent=2))
