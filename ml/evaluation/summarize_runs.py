"""Aggregate multiple seeded runs without selecting on test performance."""

import argparse
import json
from pathlib import Path

import numpy as np


def summarize(root: Path) -> dict:
    runs = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(root.glob("seed-*/metrics.json"))]
    if not runs:
        raise ValueError(f"No completed runs under {root}")
    metric_names = ("test_accuracy", "test_macro_f1", "test_weighted_f1", "test_ece")
    summary = {"runs": len(runs), "seeds": [run["seed"] for run in runs], "metrics": {}}
    for name in metric_names:
        values = [run["test_metrics"][name] for run in runs]
        summary["metrics"][name] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "values": values,
        }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.run_dir), indent=2))
