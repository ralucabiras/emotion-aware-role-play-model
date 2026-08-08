"""Export validation predictions from a frozen IEMOCAP checkpoint without retraining."""

import argparse
import json
from pathlib import Path

import numpy as np

from ml.evaluation.metrics import softmax


def _write_rows(path: Path, ids, label_ids, logits: np.ndarray, labels: list[str], temperature: float) -> None:
    probabilities = softmax(logits / temperature)
    with path.open("w", encoding="utf-8") as handle:
        for item_id, expected, row_logits, probability in zip(
            ids, label_ids, logits, probabilities, strict=True
        ):
            handle.write(
                json.dumps(
                    {
                        "id": item_id,
                        "expected": labels[int(expected)],
                        "logits": [float(value) for value in row_logits],
                        "probabilities_calibrated": {
                            label: float(probability[index]) for index, label in enumerate(labels)
                        },
                    }
                )
                + "\n"
            )


def export_text(data_root: Path, fold_dir: Path, task: str, input_field: str, max_length: int) -> Path:
    from datasets import load_from_disk
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
    )

    metrics = json.loads((fold_dir / "metrics.json").read_text(encoding="utf-8"))
    dataset = load_from_disk(str(data_root / task / f"fold-{metrics['fold']}" / "dataset"))
    tokenizer = AutoTokenizer.from_pretrained(fold_dir / "model")
    model = AutoModelForSequenceClassification.from_pretrained(fold_dir / "model")
    tokenized = dataset["validation"].map(
        lambda batch: tokenizer(batch[input_field], truncation=True, max_length=max_length),
        batched=True,
        desc=f"Tokenizing validation fold {metrics['fold']}",
    )
    output = Trainer(model=model, data_collator=DataCollatorWithPadding(tokenizer)).predict(tokenized)
    path = fold_dir / "validation_predictions.jsonl"
    _write_rows(
        path,
        dataset["validation"]["id"],
        output.label_ids,
        output.predictions,
        metrics["labels"],
        metrics["calibration"]["temperature"],
    )
    return path


def export_audio(data_root: Path, audio_root: Path, fold_dir: Path, task: str, maximum_duration: float) -> Path:
    from datasets import load_from_disk
    from transformers import (
        AutoFeatureExtractor,
        AutoModelForAudioClassification,
        Trainer,
    )

    from ml.training.train_iemocap_audio import AudioCollator, AudioDataset

    metrics = json.loads((fold_dir / "metrics.json").read_text(encoding="utf-8"))
    dataset = load_from_disk(str(data_root / task / f"fold-{metrics['fold']}" / "dataset"))
    extractor = AutoFeatureExtractor.from_pretrained(fold_dir / "model")
    model = AutoModelForAudioClassification.from_pretrained(fold_dir / "model")
    validation = AudioDataset(
        dataset["validation"],
        audio_root,
        extractor.sampling_rate,
        round(maximum_duration * extractor.sampling_rate),
    )
    output = Trainer(model=model, data_collator=AudioCollator(extractor)).predict(validation)
    path = fold_dir / "validation_predictions.jsonl"
    _write_rows(
        path,
        dataset["validation"]["id"],
        output.label_ids,
        output.predictions,
        metrics["labels"],
        metrics["calibration"]["temperature"],
    )
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--modality", choices=("text", "audio"), required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path)
    parser.add_argument("--fold-dir", type=Path, required=True)
    parser.add_argument("--task", default="benchmark_4")
    parser.add_argument("--input-field", default="context_text")
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--maximum-duration", type=float, default=20.0)
    args = parser.parse_args()
    if args.modality == "text":
        result = export_text(args.data_root, args.fold_dir, args.task, args.input_field, args.max_length)
    else:
        if args.audio_root is None:
            parser.error("--audio-root is required for audio")
        result = export_audio(
            args.data_root, args.audio_root, args.fold_dir, args.task, args.maximum_duration
        )
    print(result)
