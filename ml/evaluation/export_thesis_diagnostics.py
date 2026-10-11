"""Export aggregate IEMOCAP diagnostics used by the dissertation figures.

The input prediction rows remain under ``ml/runs`` (which is gitignored).  The
outputs contain only aggregate counts and calibration-bin statistics, so the
LaTeX document does not depend on private row-level artefacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


LABELS = ["anger", "happiness", "neutral", "sadness"]
SYSTEMS = {
    "context_text": "Context text",
    "audio": "Audio only",
    "equal_fusion": "Equal fusion",
    "validation_fitted": "Validation-fitted fusion",
    "global_calibrated": "Final global chain",
}


def load_rows(root: Path) -> list[dict]:
    rows: list[dict] = []
    for fold in range(1, 6):
        path = root / f"fold-{fold}" / "test_predictions.jsonl"
        if not path.is_file():
            raise FileNotFoundError(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                row["fold"] = fold
                rows.append(row)
    return rows


def probabilities(row: dict) -> dict[str, float]:
    values = row.get("probabilities") or row.get("probabilities_calibrated")
    if not isinstance(values, dict) or set(values) != set(LABELS):
        raise ValueError(f"Missing or invalid probabilities for {row.get('id')}")
    return {label: float(values[label]) for label in LABELS}


def aggregate(rows: list[dict], reliability_bins: int = 10, ece_bins: int = 15) -> dict:
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    bin_rows: list[list[tuple[float, bool]]] = [[] for _ in range(reliability_bins)]
    ece_rows: list[list[tuple[float, bool]]] = [[] for _ in range(ece_bins)]

    for row in rows:
        expected = row["expected"]
        predicted = row["predicted"]
        if expected not in LABELS or predicted not in LABELS:
            raise ValueError(f"Unexpected label in row {row.get('id')}")
        values = probabilities(row)
        probability_sum = sum(values.values())
        if abs(probability_sum - 1.0) > 1e-4:
            raise ValueError(f"Probabilities do not sum to one for {row.get('id')}")
        argmax = max(LABELS, key=values.__getitem__)
        if argmax != predicted:
            raise ValueError(f"Predicted label does not match probabilities for {row.get('id')}")

        expected_index = LABELS.index(expected)
        predicted_index = LABELS.index(predicted)
        matrix[expected_index][predicted_index] += 1
        confidence = values[predicted]
        bin_index = min(int(confidence * reliability_bins), reliability_bins - 1)
        bin_rows[bin_index].append((confidence, predicted == expected))
        ece_index = min(max(int(confidence * ece_bins - 1e-12), 0), ece_bins - 1)
        ece_rows[ece_index].append((confidence, predicted == expected))

    support = [sum(row) for row in matrix]
    normalized = [
        [100.0 * count / row_support for count in row]
        for row, row_support in zip(matrix, support, strict=True)
    ]
    reliability = []
    reliability_ece = 0.0
    for index, items in enumerate(bin_rows):
        count = len(items)
        mean_confidence = sum(item[0] for item in items) / count if count else None
        accuracy = sum(item[1] for item in items) / count if count else None
        if count:
            reliability_ece += count / len(rows) * abs(accuracy - mean_confidence)
        reliability.append(
            {
                "lower": index / reliability_bins,
                "upper": (index + 1) / reliability_bins,
                "count": count,
                "mean_confidence": mean_confidence,
                "accuracy": accuracy,
            }
        )

    ece = 0.0
    for items in ece_rows:
        if items:
            mean_confidence = sum(item[0] for item in items) / len(items)
            accuracy = sum(item[1] for item in items) / len(items)
            ece += len(items) / len(rows) * abs(accuracy - mean_confidence)

    correct = sum(matrix[index][index] for index in range(len(LABELS)))
    return {
        "n": len(rows),
        "accuracy": correct / len(rows),
        "ece": ece,
        "reliability_diagram_ece": reliability_ece,
        "support": support,
        "confusion_counts": matrix,
        "confusion_row_percent": normalized,
        "reliability_bins": reliability,
    }


def write_reliability_table(path: Path, bins: list[dict]) -> None:
    lines = ["lower upper count mean_confidence accuracy"]
    for item in bins:
        confidence = "nan" if item["mean_confidence"] is None else f'{item["mean_confidence"]:.8f}'
        accuracy = "nan" if item["accuracy"] is None else f'{item["accuracy"]:.8f}'
        lines.append(
            f'{item["lower"]:.1f} {item["upper"]:.1f} {item["count"]} {confidence} {accuracy}'
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_confusion_table(path: Path, aggregate_result: dict) -> None:
    lines = ["predicted expected count percent"]
    for expected_index, row in enumerate(aggregate_result["confusion_counts"]):
        for predicted_index, count in enumerate(row):
            percent = aggregate_result["confusion_row_percent"][expected_index][predicted_index]
            lines.append(f"{predicted_index} {expected_index} {count} {percent:.8f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    args.output_root.mkdir(parents=True, exist_ok=True)
    rows_by_system = {
        system: load_rows(args.input_root / system)
        for system in SYSTEMS
    }

    reference = [(row["fold"], row["id"], row["expected"]) for row in rows_by_system["context_text"]]
    for system, rows in rows_by_system.items():
        aligned = [(row["fold"], row["id"], row["expected"]) for row in rows]
        if aligned != reference:
            raise ValueError(f"Rows for {system} do not align with contextual text")

    results = {
        "labels": LABELS,
        "binning": {
            "reliability": "10 equal-width bins of maximum predicted probability; final bin includes 1.0",
            "ece": "15 equal-width bins, matching ml.evaluation.metrics.expected_calibration_error",
        },
        "systems": {},
    }
    for system, display_name in SYSTEMS.items():
        system_result = aggregate(rows_by_system[system])
        system_result["display_name"] = display_name
        results["systems"][system] = system_result
        write_reliability_table(
            args.output_root / f"reliability_{system}.dat",
            system_result["reliability_bins"],
        )
        write_confusion_table(
            args.output_root / f"confusion_{system}.dat",
            system_result,
        )

    (args.output_root / "model_diagnostics.json").write_text(
        json.dumps(results, indent=2) + "\n",
        encoding="utf-8",
    )
    for system, result in results["systems"].items():
        print(
            f'{system}: n={result["n"]}, accuracy={result["accuracy"]:.4f}, '
            f'ECE={result["ece"]:.4f}'
        )


if __name__ == "__main__":
    main()
