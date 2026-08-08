import json
from pathlib import Path

import pytest
from ml.evaluation.fuse_iemocap_modalities import fuse

LABELS = ["anger", "happiness", "neutral", "sadness"]


def _write_experiment(root: Path, probabilities: dict[str, float]) -> None:
    for fold in range(1, 6):
        fold_dir = root / f"fold-{fold}"
        fold_dir.mkdir(parents=True)
        item_id = f"Ses0{fold}F_impro01_F000"
        expected = LABELS[(fold - 1) % len(LABELS)]
        row_probabilities = {label: probabilities.get(label, 0.0) for label in LABELS}
        predicted = max(row_probabilities, key=row_probabilities.get)
        correct = predicted == expected
        (fold_dir / "metrics.json").write_text(
            json.dumps(
                {
                    "fold": fold,
                    "labels": LABELS,
                    "test_metrics": {
                        "test_accuracy": float(correct),
                        "test_macro_f1": 0.25 if correct else 0.0,
                        "test_weighted_f1": float(correct),
                    },
                }
            ),
            encoding="utf-8",
        )
        (fold_dir / "test_predictions.jsonl").write_text(
            json.dumps(
                {
                    "id": item_id,
                    "expected": expected,
                    "predicted": predicted,
                    "probabilities_calibrated": row_probabilities,
                }
            )
            + "\n",
            encoding="utf-8",
        )


def test_equal_fusion_pairs_ids_and_writes_auditable_result(tmp_path: Path) -> None:
    text_dir, audio_dir = tmp_path / "text", tmp_path / "audio"
    _write_experiment(text_dir, {"anger": 0.4, "happiness": 0.3, "neutral": 0.2, "sadness": 0.1})
    _write_experiment(audio_dir, {"anger": 0.1, "happiness": 0.2, "neutral": 0.3, "sadness": 0.4})

    result = fuse(text_dir, audio_dir, tmp_path / "fusion", iterations=100, seed=7)

    assert result["text_weight"] == 0.5
    assert result["pooled"]["accuracy"] == pytest.approx(0.4)
    assert result["paired_dialogue_bootstrap"]["utterances"] == 5
    assert (tmp_path / "fusion" / "summary.json").exists()


def test_fusion_rejects_test_id_mismatch(tmp_path: Path) -> None:
    text_dir, audio_dir = tmp_path / "text", tmp_path / "audio"
    values = {"anger": 0.4, "happiness": 0.3, "neutral": 0.2, "sadness": 0.1}
    _write_experiment(text_dir, values)
    _write_experiment(audio_dir, values)
    path = audio_dir / "fold-3" / "test_predictions.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["id"] = "Ses03F_impro99_F999"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Prediction ids differ"):
        fuse(text_dir, audio_dir, tmp_path / "fusion", iterations=100)
