"""Leakage-free late fusion of paired IEMOCAP out-of-fold predictions."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from ml.evaluation.metrics import expected_calibration_error
from ml.evaluation.paired_cluster_bootstrap import (
    compare,
    confusion_matrix,
    dialogue_id,
    metrics_from_confusion,
)


def _read_fold(root: Path, fold: int) -> tuple[dict, dict[str, dict]]:
    fold_dir = root / f"fold-{fold}"
    metrics = json.loads((fold_dir / "metrics.json").read_text(encoding="utf-8"))
    rows = {
        row["id"]: row
        for row in map(
            json.loads,
            (fold_dir / "test_predictions.jsonl").read_text(encoding="utf-8").splitlines(),
        )
    }
    if metrics["fold"] != fold or not rows:
        raise ValueError(f"Invalid or empty fold {fold} in {root}")
    return metrics, rows


def _classification_summary(expected: list[str], predicted: list[str], labels: list[str]) -> dict:
    matrix = confusion_matrix(expected, predicted, labels)
    metrics = metrics_from_confusion(matrix)
    true_positive = np.diag(matrix).astype(float)
    predicted_counts = matrix.sum(axis=0)
    support = matrix.sum(axis=1)
    precision = np.divide(
        true_positive, predicted_counts, out=np.zeros_like(true_positive), where=predicted_counts != 0
    )
    recall = np.divide(true_positive, support, out=np.zeros_like(true_positive), where=support != 0)
    return {
        "accuracy": metrics["accuracy"],
        "macro_f1": metrics["macro_f1"],
        "weighted_f1": metrics["weighted_f1"],
        "per_class": {
            label: {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(metrics["per_class_f1"][index]),
                "support": int(support[index]),
            }
            for index, label in enumerate(labels)
        },
    }


def _rename_bootstrap(result: dict) -> dict:
    for metrics in (result["observed"], result["per_class_f1"]):
        for values in metrics.values():
            values["text_context"] = values.pop("baseline")
            values["fusion"] = values.pop("context")
    result["comparison"] = "fusion_minus_text_context"
    return result


def fuse(
    text_dir: Path,
    audio_dir: Path,
    output_dir: Path,
    text_weight: float = 0.5,
    iterations: int = 10_000,
    seed: int = 20260808,
) -> dict:
    """Average calibrated posteriors using a fixed, predeclared modality weight."""
    if not 0.0 <= text_weight <= 1.0:
        raise ValueError("text_weight must be between zero and one")
    output_dir.mkdir(parents=True, exist_ok=True)
    labels = None
    all_expected: list[str] = []
    all_predicted: list[str] = []
    all_probabilities: list[list[float]] = []
    fold_summaries = []
    grouped: dict[str, list[dict]] = defaultdict(list)
    seen_ids: set[str] = set()

    for fold in range(1, 6):
        text_metrics, text_rows = _read_fold(text_dir, fold)
        audio_metrics, audio_rows = _read_fold(audio_dir, fold)
        if text_metrics["labels"] != audio_metrics["labels"]:
            raise ValueError(f"Label order differs in fold {fold}")
        if labels is None:
            labels = text_metrics["labels"]
        elif labels != text_metrics["labels"]:
            raise ValueError("Label order differs across folds")
        if text_rows.keys() != audio_rows.keys():
            raise ValueError(f"Prediction ids differ in fold {fold}")
        for modality, metrics, rows in (
            ("text", text_metrics, text_rows),
            ("audio", audio_metrics, audio_rows),
        ):
            row_values = list(rows.values())
            reconstructed = _classification_summary(
                [row["expected"] for row in row_values],
                [row["predicted"] for row in row_values],
                labels,
            )
            for metric_name in ("accuracy", "macro_f1", "weighted_f1"):
                recorded = metrics["test_metrics"][f"test_{metric_name}"]
                if not np.isclose(reconstructed[metric_name], recorded, atol=1e-12):
                    raise ValueError(
                        f"{modality} fold {fold} predictions do not match recorded {metric_name}"
                    )
        if duplicate := seen_ids & text_rows.keys():
            raise ValueError(f"Test ids occur in multiple folds: {sorted(duplicate)[:3]}")
        seen_ids.update(text_rows)

        fold_expected: list[str] = []
        fold_predicted: list[str] = []
        fold_probabilities: list[list[float]] = []
        output_rows = []
        for item_id, text_row in text_rows.items():
            audio_row = audio_rows[item_id]
            if text_row["expected"] != audio_row["expected"]:
                raise ValueError(f"Expected label differs for {item_id}")
            text_probability = np.asarray(
                [text_row["probabilities_calibrated"][label] for label in labels]
            )
            audio_probability = np.asarray(
                [audio_row["probabilities_calibrated"][label] for label in labels]
            )
            probability = text_weight * text_probability + (1.0 - text_weight) * audio_probability
            predicted = labels[int(probability.argmax())]
            expected = text_row["expected"]
            fold_expected.append(expected)
            fold_predicted.append(predicted)
            fold_probabilities.append(probability.tolist())
            grouped[dialogue_id(item_id)].append(
                {
                    "id": item_id,
                    "expected": expected,
                    "baseline": text_row["predicted"],
                    "context": predicted,
                }
            )
            output_rows.append(
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
        summary = _classification_summary(fold_expected, fold_predicted, labels)
        summary["ece"] = expected_calibration_error(
            np.asarray(fold_probabilities), np.asarray([labels.index(value) for value in fold_expected])
        )
        summary["fold"] = fold
        fold_summaries.append(summary)
        fold_dir = output_dir / f"fold-{fold}"
        fold_dir.mkdir(exist_ok=True)
        with (fold_dir / "test_predictions.jsonl").open("w", encoding="utf-8") as handle:
            for row in output_rows:
                handle.write(json.dumps(row) + "\n")
        (fold_dir / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        all_expected.extend(fold_expected)
        all_predicted.extend(fold_predicted)
        all_probabilities.extend(fold_probabilities)

    if labels is None:
        raise ValueError("No paired predictions found")
    pooled = _classification_summary(all_expected, all_predicted, labels)
    pooled["ece"] = expected_calibration_error(
        np.asarray(all_probabilities), np.asarray([labels.index(value) for value in all_expected])
    )
    bootstrap = _rename_bootstrap(compare(labels, dict(grouped), iterations, seed))
    result = {
        "experiment": "iemocap_benchmark4_context3_audio_equal_fusion",
        "task": "benchmark_4",
        "method": "fixed_weight_average_of_validation_calibrated_posteriors",
        "text_experiment": text_dir.name,
        "audio_experiment": audio_dir.name,
        "text_weight": text_weight,
        "audio_weight": 1.0 - text_weight,
        "folds": fold_summaries,
        "pooled": pooled,
        "paired_dialogue_bootstrap": bootstrap,
    }
    (output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-dir", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--text-weight", type=float, default=0.5)
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260808)
    args = parser.parse_args()
    fusion = fuse(
        args.text_dir,
        args.audio_dir,
        args.output_dir,
        args.text_weight,
        args.iterations,
        args.seed,
    )
    print(json.dumps(fusion, indent=2))
