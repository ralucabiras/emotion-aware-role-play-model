import json
from pathlib import Path

import numpy as np
import pytest
from ml.evaluation.calibrate_iemocap_fusion import fit_parameters, probability_metrics, run_global_oof
from ml.evaluation.export_iemocap_validation import _write_rows


def test_validation_fit_prefers_informative_modality() -> None:
    expected = np.asarray([0, 1, 0, 1])
    text = np.asarray([[0.9, 0.1], [0.1, 0.9], [0.8, 0.2], [0.2, 0.8]])
    audio = np.asarray([[0.2, 0.8], [0.8, 0.2], [0.3, 0.7], [0.7, 0.3]])

    weight, temperature, nll = fit_parameters(text, audio, expected)

    assert weight > 0.5
    assert temperature > 0
    assert nll < np.log(2)


def test_validation_export_includes_logits_and_calibrated_probabilities(tmp_path: Path) -> None:
    output = tmp_path / "validation_predictions.jsonl"
    _write_rows(output, ["u1"], np.asarray([1]), np.asarray([[1.0, 2.0]]), ["a", "b"], 2.0)

    row = json.loads(output.read_text(encoding="utf-8"))
    assert row["id"] == "u1"
    assert row["expected"] == "b"
    assert row["logits"] == [1.0, 2.0]
    assert sum(row["probabilities_calibrated"].values()) == pytest.approx(1.0)


def test_probability_metrics_report_proper_scores_and_reliability() -> None:
    probabilities = np.asarray([[0.8, 0.2], [0.25, 0.75]])
    result = probability_metrics(probabilities, np.asarray([0, 1]))

    assert result["nll"] > 0
    assert result["multiclass_brier"] == pytest.approx(0.1025)
    assert sum(item["count"] for item in result["reliability_bins"]) == 2


def test_global_oof_fit_produces_one_deployment_parameter_set(tmp_path: Path) -> None:
    labels = ["negative", "positive"]
    for modality, probabilities in (
        ("text", {"negative": 0.8, "positive": 0.2}),
        ("audio", {"negative": 0.6, "positive": 0.4}),
    ):
        for fold in range(1, 6):
            fold_dir = tmp_path / modality / f"fold-{fold}"
            fold_dir.mkdir(parents=True)
            (fold_dir / "metrics.json").write_text(
                json.dumps({"labels": labels, "fold": fold, "calibration": {"temperature": 1.0}}),
                encoding="utf-8",
            )
            for split in ("validation", "test"):
                row = {
                    "id": f"Ses0{fold}F_impro01_F000",
                    "expected": "negative",
                    "probabilities_calibrated": probabilities,
                }
                if split == "test":
                    row["predicted"] = "negative"
                else:
                    row["logits"] = [float(np.log(probabilities[label])) for label in labels]
                (fold_dir / f"{split}_predictions.jsonl").write_text(
                    json.dumps(row) + "\n", encoding="utf-8"
                )

    result = run_global_oof(tmp_path / "text", tmp_path / "audio", tmp_path / "output")

    assert result["validation_examples"] == 5
    assert result["text_weight"] >= 0.5
    assert result["pooled"]["accuracy"] == 1.0
    assert (tmp_path / "output" / "fold-5" / "test_predictions.jsonl").exists()
