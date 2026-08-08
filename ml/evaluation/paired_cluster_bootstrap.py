"""Paired dialogue-cluster bootstrap for IEMOCAP experiment comparisons."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def dialogue_id(utterance_id: str) -> str:
    parts = utterance_id.rsplit("_", 1)
    if len(parts) != 2 or not parts[1] or parts[1][0] not in {"F", "M"}:
        raise ValueError(f"Cannot derive dialogue id from {utterance_id!r}")
    return parts[0]


def confusion_matrix(expected: list[str], predicted: list[str], labels: list[str]) -> np.ndarray:
    label_ids = {label: index for index, label in enumerate(labels)}
    try:
        expected_ids = np.asarray([label_ids[label] for label in expected])
        predicted_ids = np.asarray([label_ids[label] for label in predicted])
    except KeyError as error:
        raise ValueError(f"Prediction contains unknown label: {error.args[0]}") from error
    encoded = expected_ids * len(labels) + predicted_ids
    return np.bincount(encoded, minlength=len(labels) ** 2).reshape(len(labels), len(labels))


def metrics_from_confusion(matrix: np.ndarray) -> dict[str, np.ndarray | float]:
    true_positive = np.diag(matrix).astype(float)
    predicted = matrix.sum(axis=0)
    support = matrix.sum(axis=1)
    precision = np.divide(true_positive, predicted, out=np.zeros_like(true_positive), where=predicted != 0)
    recall = np.divide(true_positive, support, out=np.zeros_like(true_positive), where=support != 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(precision), where=(precision + recall) != 0)
    total = matrix.sum()
    return {
        "accuracy": float(true_positive.sum() / total) if total else 0.0,
        "macro_f1": float(f1.mean()),
        "weighted_f1": float(np.average(f1, weights=support)) if total else 0.0,
        "per_class_f1": f1,
    }


def load_paired_predictions(baseline_dir: Path, context_dir: Path) -> tuple[list[str], dict[str, list[dict]]]:
    labels = None
    grouped: dict[str, list[dict]] = defaultdict(list)
    seen_ids = set()
    for fold in range(1, 6):
        baseline_metrics = json.loads((baseline_dir / f"fold-{fold}" / "metrics.json").read_text(encoding="utf-8"))
        context_metrics = json.loads((context_dir / f"fold-{fold}" / "metrics.json").read_text(encoding="utf-8"))
        if baseline_metrics["labels"] != context_metrics["labels"]:
            raise ValueError(f"Label order differs in fold {fold}")
        if labels is None:
            labels = baseline_metrics["labels"]
        elif labels != baseline_metrics["labels"]:
            raise ValueError("Label order differs across folds")
        baseline_rows = {
            row["id"]: row
            for row in map(
                json.loads,
                (baseline_dir / f"fold-{fold}" / "test_predictions.jsonl").read_text(encoding="utf-8").splitlines(),
            )
        }
        context_rows = {
            row["id"]: row
            for row in map(
                json.loads,
                (context_dir / f"fold-{fold}" / "test_predictions.jsonl").read_text(encoding="utf-8").splitlines(),
            )
        }
        if baseline_rows.keys() != context_rows.keys():
            raise ValueError(f"Prediction ids differ in fold {fold}")
        for name, rows, metrics in (
            ("baseline", baseline_rows, baseline_metrics),
            ("context", context_rows, context_metrics),
        ):
            ordered_rows = list(rows.values())
            calculated = metrics_from_confusion(
                confusion_matrix(
                    [row["expected"] for row in ordered_rows],
                    [row["predicted"] for row in ordered_rows],
                    metrics["labels"],
                )
            )
            for metric_name in ("accuracy", "macro_f1", "weighted_f1"):
                recorded = metrics["test_metrics"][f"test_{metric_name}"]
                if not np.isclose(calculated[metric_name], recorded, atol=1e-12):
                    raise ValueError(
                        f"{name} fold {fold} predictions do not match recorded {metric_name}: "
                        f"{calculated[metric_name]} != {recorded}"
                    )
        if duplicate := seen_ids & baseline_rows.keys():
            raise ValueError(f"Test ids occur in multiple folds: {sorted(duplicate)[:3]}")
        seen_ids.update(baseline_rows)
        for item_id, baseline in baseline_rows.items():
            context = context_rows[item_id]
            if baseline["expected"] != context["expected"]:
                raise ValueError(f"Expected label differs for {item_id}")
            grouped[dialogue_id(item_id)].append(
                {
                    "id": item_id,
                    "expected": baseline["expected"],
                    "baseline": baseline["predicted"],
                    "context": context["predicted"],
                }
            )
    if labels is None or not grouped:
        raise ValueError("No paired predictions found")
    return labels, dict(grouped)


def interval(values: np.ndarray) -> dict[str, float]:
    return {
        "lower_95": float(np.percentile(values, 2.5)),
        "upper_95": float(np.percentile(values, 97.5)),
        "bootstrap_mean": float(values.mean()),
        "bootstrap_std": float(values.std()),
        "probability_improvement": float((np.count_nonzero(values > 0) + 1) / (len(values) + 1)),
    }


def compare(
    labels: list[str],
    grouped: dict[str, list[dict]],
    iterations: int = 10_000,
    seed: int = 20260808,
) -> dict:
    if iterations < 100:
        raise ValueError("Use at least 100 bootstrap iterations")
    clusters = sorted(grouped)
    baseline_matrices = []
    context_matrices = []
    for cluster in clusters:
        rows = grouped[cluster]
        expected = [row["expected"] for row in rows]
        baseline_matrices.append(confusion_matrix(expected, [row["baseline"] for row in rows], labels))
        context_matrices.append(confusion_matrix(expected, [row["context"] for row in rows], labels))
    baseline_stack = np.asarray(baseline_matrices)
    context_stack = np.asarray(context_matrices)
    baseline_observed = metrics_from_confusion(baseline_stack.sum(axis=0))
    context_observed = metrics_from_confusion(context_stack.sum(axis=0))
    rng = np.random.default_rng(seed)
    scalar_names = ("accuracy", "macro_f1", "weighted_f1")
    scalar_differences = {name: np.empty(iterations) for name in scalar_names}
    class_differences = np.empty((iterations, len(labels)))
    for iteration in range(iterations):
        sampled = rng.integers(0, len(clusters), size=len(clusters))
        baseline = metrics_from_confusion(baseline_stack[sampled].sum(axis=0))
        context = metrics_from_confusion(context_stack[sampled].sum(axis=0))
        for name in scalar_names:
            scalar_differences[name][iteration] = context[name] - baseline[name]
        class_differences[iteration] = context["per_class_f1"] - baseline["per_class_f1"]
    return {
        "method": "paired_percentile_cluster_bootstrap",
        "resampling_unit": "dialogue",
        "iterations": iterations,
        "seed": seed,
        "dialogues": len(clusters),
        "utterances": int(baseline_stack.sum()),
        "labels": labels,
        "observed": {
            name: {
                "baseline": float(baseline_observed[name]),
                "context": float(context_observed[name]),
                "difference": float(context_observed[name] - baseline_observed[name]),
                **interval(scalar_differences[name]),
            }
            for name in scalar_names
        },
        "per_class_f1": {
            label: {
                "baseline": float(baseline_observed["per_class_f1"][index]),
                "context": float(context_observed["per_class_f1"][index]),
                "difference": float(
                    context_observed["per_class_f1"][index] - baseline_observed["per_class_f1"][index]
                ),
                **interval(class_differences[:, index]),
            }
            for index, label in enumerate(labels)
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--context-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260808)
    args = parser.parse_args()
    task_labels, paired = load_paired_predictions(args.baseline_dir, args.context_dir)
    result = compare(task_labels, paired, args.iterations, args.seed)
    result["baseline_experiment"] = args.baseline_dir.name
    result["context_experiment"] = args.context_dir.name
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
