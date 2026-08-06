"""Aggregate five speaker-independent IEMOCAP fold results."""

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_recall_fscore_support,
)

METRICS = ("test_accuracy", "test_macro_f1", "test_weighted_f1", "test_ece")


def summarize(experiment_dir: Path) -> dict:
    runs = []
    expected_all = []
    predicted_all = []
    labels = None
    seen_ids = set()
    for fold in range(1, 6):
        fold_dir = experiment_dir / f"fold-{fold}"
        metrics = json.loads((fold_dir / "metrics.json").read_text(encoding="utf-8"))
        if metrics["fold"] != fold:
            raise ValueError(f"Fold metadata mismatch in {fold_dir}")
        if labels is None:
            labels = metrics["labels"]
        elif labels != metrics["labels"]:
            raise ValueError("Label order differs across folds")
        rows = [json.loads(line) for line in (fold_dir / "test_predictions.jsonl").read_text(encoding="utf-8").splitlines()]
        duplicate_ids = seen_ids & {row["id"] for row in rows}
        if duplicate_ids:
            raise ValueError(f"Test utterances occur in multiple folds: {sorted(duplicate_ids)[:3]}")
        seen_ids.update(row["id"] for row in rows)
        expected_all.extend(row["expected"] for row in rows)
        predicted_all.extend(row["predicted"] for row in rows)
        runs.append(metrics)
    fold_metrics = {
        metric: {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "values": values,
        }
        for metric in METRICS
        if (values := [run["test_metrics"][metric] for run in runs])
    }
    precision, recall, f1, support = precision_recall_fscore_support(
        expected_all, predicted_all, labels=labels, zero_division=0
    )
    pooled_per_class = {
        label: {
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(f1[index]),
            "support": int(support[index]),
        }
        for index, label in enumerate(labels)
    }
    result = {
        "experiment": runs[0]["experiment"],
        "task": runs[0]["task"],
        "folds": 5,
        "seed": runs[0]["seed"],
        "fold_metrics": fold_metrics,
        "pooled": {
            "examples": len(expected_all),
            "accuracy": float(accuracy_score(expected_all, predicted_all)),
            "macro_f1": float(f1_score(expected_all, predicted_all, average="macro", zero_division=0)),
            "weighted_f1": float(f1_score(expected_all, predicted_all, average="weighted", zero_division=0)),
            "per_class": pooled_per_class,
        },
    }
    (experiment_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.experiment_dir), indent=2))
