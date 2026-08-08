"""Fine-tune Wav2Vec2 on one speaker-independent IEMOCAP audio fold."""

import argparse
import json
import math
import os
import platform
import random
from datetime import UTC, datetime
from pathlib import Path

import numpy as np


class AudioDataset:
    def __init__(self, rows, audio_root: Path, sampling_rate: int, maximum_samples: int) -> None:
        self.rows = rows
        self.audio_root = audio_root
        self.sampling_rate = sampling_rate
        self.maximum_samples = maximum_samples

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict:
        import soundfile as sf
        from scipy.signal import resample_poly

        row = self.rows[index]
        path = self.audio_root / "audio" / f"{row['id']}.wav"
        waveform, rate = sf.read(path, dtype="float32", always_2d=False)
        if waveform.ndim != 1:
            waveform = waveform.mean(axis=1)
        if rate != self.sampling_rate:
            divisor = math.gcd(rate, self.sampling_rate)
            waveform = resample_poly(waveform, self.sampling_rate // divisor, rate // divisor).astype(np.float32)
        return {"input_values": waveform[: self.maximum_samples], "labels": int(row["label"])}


class AudioCollator:
    def __init__(self, feature_extractor) -> None:
        self.feature_extractor = feature_extractor

    def __call__(self, features: list[dict]) -> dict:
        import torch

        batch = self.feature_extractor.pad(
            [{"input_values": feature["input_values"]} for feature in features],
            padding=True,
            return_tensors="pt",
        )
        batch["labels"] = torch.tensor([feature["labels"] for feature in features], dtype=torch.long)
        return batch


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_everything(seed: int) -> None:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def audio_audit(rows, audio_root: Path, maximum_duration: float) -> dict:
    import soundfile as sf

    rates = {}
    missing = []
    truncated = 0
    durations = []
    for row in rows:
        path = audio_root / "audio" / f"{row['id']}.wav"
        if not path.is_file():
            missing.append(row["id"])
            continue
        info = sf.info(path)
        rates[info.samplerate] = rates.get(info.samplerate, 0) + 1
        duration = info.frames / info.samplerate
        durations.append(duration)
        truncated += duration > maximum_duration
    if missing:
        raise ValueError(f"Missing {len(missing)} audio files; first: {missing[:3]}")
    return {
        "files": len(rows),
        "sample_rate_counts": {str(key): value for key, value in sorted(rates.items())},
        "maximum_duration_seconds": maximum_duration,
        "truncated_files": truncated,
        "longest_seconds": max(durations),
    }


def run(config_path: Path, data_root: Path, audio_root: Path, output_root: Path, fold: int, seed: int) -> dict:
    import datasets
    import soundfile
    import torch
    import transformers
    from datasets import load_from_disk
    from transformers import (
        AutoFeatureExtractor,
        AutoModelForAudioClassification,
        EarlyStoppingCallback,
        Trainer,
        TrainingArguments,
    )

    from ml.evaluation.export_iemocap_validation import _write_rows
    from ml.evaluation.metrics import (
        classification_metrics,
        expected_calibration_error,
        fit_temperature,
        negative_log_likelihood,
        per_class_metrics,
        softmax,
    )
    from ml.training.train_meld import plot_confusion

    config = load_config(config_path)
    if fold not in range(1, 6):
        raise ValueError("fold must be between 1 and 5")
    seed_everything(seed)
    labels = config["labels"]
    id2label = dict(enumerate(labels))
    label2id = {label: index for index, label in id2label.items()}
    dataset = load_from_disk(str(data_root / config["task"] / f"fold-{fold}" / "dataset"))
    all_rows = [row for split in ("train", "validation", "test") for row in dataset[split]]
    audit = audio_audit(all_rows, audio_root, config["maximum_duration_seconds"])
    feature_extractor = AutoFeatureExtractor.from_pretrained(config["model_name"])
    if feature_extractor.sampling_rate != config["sampling_rate"]:
        raise ValueError("Configured sampling rate differs from the model feature extractor")
    maximum_samples = round(config["maximum_duration_seconds"] * config["sampling_rate"])
    torch_datasets = {
        split: AudioDataset(dataset[split], audio_root, config["sampling_rate"], maximum_samples)
        for split in ("train", "validation", "test")
    }
    run_dir = output_root / config["experiment_name"] / f"fold-{fold}"
    run_dir.mkdir(parents=True, exist_ok=True)
    model = AutoModelForAudioClassification.from_pretrained(
        config["model_name"],
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
        dtype=torch.float32,
    )
    if config["freeze_feature_encoder"]:
        if hasattr(model, "freeze_feature_encoder"):
            model.freeze_feature_encoder()
        else:
            model.wav2vec2.feature_extractor._freeze_parameters()

    def compute_metrics(prediction):
        return classification_metrics(prediction.predictions, prediction.label_ids)

    batches_per_epoch = math.ceil(len(dataset["train"]) / config["train_batch_size"])
    optimizer_steps = math.ceil(batches_per_epoch / config["gradient_accumulation_steps"]) * config["epochs"]
    warmup_steps = round(optimizer_steps * config["warmup_ratio"])
    arguments = TrainingArguments(
        output_dir=str(run_dir / "checkpoints"),
        learning_rate=config["learning_rate"],
        per_device_train_batch_size=config["train_batch_size"],
        per_device_eval_batch_size=config["eval_batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation_steps"],
        num_train_epochs=config["epochs"],
        weight_decay=config["weight_decay"],
        warmup_steps=warmup_steps,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="steps",
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model=config["metric_for_best_model"],
        greater_is_better=config["greater_is_better"],
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        gradient_checkpointing=config["gradient_checkpointing"],
        dataloader_num_workers=2,
        report_to="none",
        seed=seed,
        data_seed=seed,
    )
    trainer = Trainer(
        model=model,
        args=arguments,
        train_dataset=torch_datasets["train"],
        eval_dataset=torch_datasets["validation"],
        processing_class=feature_extractor,
        data_collator=AudioCollator(feature_extractor),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=config["early_stopping_patience"])],
    )
    train_result = trainer.train()
    trainer.remove_callback(EarlyStoppingCallback)
    validation_output = trainer.predict(torch_datasets["validation"], metric_key_prefix="validation")
    test_output = trainer.predict(torch_datasets["test"], metric_key_prefix="test")
    temperature = fit_temperature(validation_output.predictions, validation_output.label_ids)
    raw_probabilities = softmax(test_output.predictions)
    calibrated_probabilities = softmax(test_output.predictions / temperature)
    predictions = raw_probabilities.argmax(axis=1)
    test_metrics = dict(test_output.metrics)
    test_metrics["test_calibrated_ece"] = expected_calibration_error(calibrated_probabilities, test_output.label_ids)
    test_metrics["test_calibrated_nll"] = negative_log_likelihood(
        test_output.predictions, test_output.label_ids, temperature
    )
    model_dir = run_dir / "model"
    trainer.save_model(model_dir)
    feature_extractor.save_pretrained(model_dir)
    export = {
        "experiment": config["experiment_name"],
        "task": config["task"],
        "modality": "audio",
        "fold": fold,
        "seed": seed,
        "created_at": datetime.now(UTC).isoformat(),
        "base_model": config["model_name"],
        "labels": labels,
        "split_sessions": {
            split: sorted(set(dataset[split]["session"])) for split in ("train", "validation", "test")
        },
        "audio_audit": audit,
        "train_metrics": train_result.metrics,
        "validation_metrics": validation_output.metrics,
        "test_metrics": test_metrics,
        "calibration": {
            "method": "validation_temperature_scaling",
            "temperature": temperature,
            "validation_nll_before": negative_log_likelihood(
                validation_output.predictions, validation_output.label_ids
            ),
            "validation_nll_after": negative_log_likelihood(
                validation_output.predictions, validation_output.label_ids, temperature
            ),
        },
        "test_per_class": per_class_metrics(test_output.label_ids, predictions, labels),
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "datasets": datasets.__version__,
            "soundfile": soundfile.__version__,
            "precision": "fp16-mixed" if torch.cuda.is_available() else "fp32",
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        },
    }
    (run_dir / "metrics.json").write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
    _write_rows(
        run_dir / "validation_predictions.jsonl",
        dataset["validation"]["id"],
        validation_output.label_ids,
        validation_output.predictions,
        labels,
        temperature,
    )
    with (run_dir / "test_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for item_id, expected, predicted, raw_probability, calibrated_probability in zip(
            dataset["test"]["id"],
            test_output.label_ids,
            predictions,
            raw_probabilities,
            calibrated_probabilities,
            strict=True,
        ):
            handle.write(
                json.dumps(
                    {
                        "id": item_id,
                        "expected": labels[int(expected)],
                        "predicted": labels[int(predicted)],
                        "confidence_raw": float(raw_probability.max()),
                        "confidence_calibrated": float(calibrated_probability.max()),
                        "probabilities_calibrated": {
                            label: float(calibrated_probability[index]) for index, label in enumerate(labels)
                        },
                    }
                )
                + "\n"
            )
    plot_confusion(test_output.label_ids, predictions, labels, run_dir / "confusion_matrix.png")
    return export


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    print(json.dumps(run(args.config, args.data_root, args.audio_root, args.output_root, args.fold, args.seed), indent=2))
