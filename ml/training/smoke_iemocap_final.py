"""Private integrity smoke test for final full-data multimodal artifacts."""

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from ml.evaluation.metrics import softmax
from ml.training.train_iemocap_final import load_full_dataset


def balanced_rows(dataset, labels: list[str], examples_per_class: int):
    selected = []
    counts = Counter()
    for row in dataset:
        label = labels[int(row["label"])]
        if counts[label] < examples_per_class:
            selected.append(row)
            counts[label] += 1
        if all(counts[label] == examples_per_class for label in labels):
            break
    if any(counts[label] != examples_per_class for label in labels):
        raise ValueError(f"Could not build balanced smoke sample: {dict(counts)}")
    return selected


def run(
    config_path: Path,
    text_model: Path,
    audio_model: Path,
    data_root: Path,
    audio_root: Path,
    examples_per_class: int,
) -> dict:
    import torch
    from transformers import (
        AutoFeatureExtractor,
        AutoModelForAudioClassification,
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
    )

    from ml.training.train_iemocap_audio import AudioCollator, AudioDataset

    config = json.loads(config_path.read_text(encoding="utf-8"))
    labels, calibration = config["labels"], config["calibration"]
    rows = balanced_rows(
        load_full_dataset(data_root, config["task"]), labels, examples_per_class
    )
    expected = np.asarray([int(row["label"]) for row in rows])

    tokenizer = AutoTokenizer.from_pretrained(text_model)
    text_network = AutoModelForSequenceClassification.from_pretrained(text_model).eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    text_network.to(device)
    text_logits = []
    for start in range(0, len(rows), 16):
        texts = [row[config["text"]["input_field"]] for row in rows[start : start + 16]]
        encoded = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=config["text"]["max_length"],
            return_tensors="pt",
        ).to(device)
        with torch.inference_mode():
            text_logits.extend(text_network(**encoded).logits.float().cpu().numpy())
    text_logits = np.asarray(text_logits)
    del text_network
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    extractor = AutoFeatureExtractor.from_pretrained(audio_model)
    audio_network = AutoModelForAudioClassification.from_pretrained(audio_model)
    audio_dataset = AudioDataset(
        rows,
        audio_root,
        config["audio"]["sampling_rate"],
        round(config["audio"]["maximum_duration_seconds"] * config["audio"]["sampling_rate"]),
    )
    audio_output = Trainer(
        model=audio_network,
        data_collator=AudioCollator(extractor),
    ).predict(audio_dataset)
    audio_logits = np.asarray(audio_output.predictions)
    if not np.isfinite(text_logits).all() or not np.isfinite(audio_logits).all():
        raise RuntimeError("A final model produced non-finite logits")

    text_probabilities = softmax(text_logits / calibration["text_temperature"])
    audio_probabilities = softmax(audio_logits / calibration["audio_temperature"])
    fused = calibration["text_weight"] * text_probabilities + calibration["audio_weight"] * audio_probabilities
    fused_probabilities = softmax(
        np.log(np.clip(fused, 1e-12, 1.0)) / calibration["fusion_temperature"]
    )

    def diagnostic(probabilities: np.ndarray) -> dict:
        predicted = probabilities.argmax(axis=1)
        return {
            "finite": bool(np.isfinite(probabilities).all()),
            "predicted_label_counts": {
                labels[index]: int((predicted == index).sum()) for index in range(len(labels))
            },
            "balanced_training_sample_accuracy_not_for_evaluation": float((predicted == expected).mean()),
            "mean_confidence": float(probabilities.max(axis=1).mean()),
        }

    result = {
        "purpose": "artifact_integrity_only_not_model_evaluation",
        "examples": len(rows),
        "examples_per_class": examples_per_class,
        "text": diagnostic(text_probabilities),
        "audio": diagnostic(audio_probabilities),
        "fusion": diagnostic(fused_probabilities),
    }
    for modality in ("text", "audio", "fusion"):
        predicted_classes = sum(value > 0 for value in result[modality]["predicted_label_counts"].values())
        if not result[modality]["finite"] or predicted_classes < 2:
            raise RuntimeError(f"{modality} artifact failed integrity gate: {result[modality]}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--text-model", type=Path, required=True)
    parser.add_argument("--audio-model", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--examples-per-class", type=int, default=32)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(
        args.config,
        args.text_model,
        args.audio_model,
        args.data_root,
        args.audio_root,
        args.examples_per_class,
    )
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
