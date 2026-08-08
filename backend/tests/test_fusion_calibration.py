import json
from pathlib import Path

import numpy as np
import pytest
from ml.evaluation.calibrate_iemocap_fusion import fit_parameters
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
