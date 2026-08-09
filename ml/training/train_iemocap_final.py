"""Train final IEMOCAP text or audio artifact on all unique benchmark rows."""

import argparse
import json
import math
import platform
from datetime import UTC, datetime
from pathlib import Path


def load_full_dataset(data_root: Path, task: str):
    from datasets import concatenate_datasets, load_from_disk

    fold = load_from_disk(str(data_root / task / "fold-1" / "dataset"))
    dataset = concatenate_datasets([fold[split] for split in ("train", "validation", "test")])
    ids = dataset["id"]
    if len(ids) != len(set(ids)):
        raise ValueError("Full-data assembly contains duplicate utterance ids")
    if len(ids) != 5531:
        raise ValueError(f"Expected 5531 benchmark rows, found {len(ids)}")
    return dataset


def _arguments(run_dir: Path, settings: dict, epochs: int, seed: int, gradient_checkpointing: bool = False):
    import torch
    from transformers import TrainingArguments

    batches = math.ceil(5531 / settings["train_batch_size"])
    optimizer_steps = math.ceil(batches / settings["gradient_accumulation_steps"]) * epochs
    return TrainingArguments(
        output_dir=str(run_dir / "trainer-output"),
        learning_rate=settings["learning_rate"],
        per_device_train_batch_size=settings["train_batch_size"],
        gradient_accumulation_steps=settings["gradient_accumulation_steps"],
        num_train_epochs=epochs,
        weight_decay=settings["weight_decay"],
        warmup_steps=round(optimizer_steps * settings["warmup_ratio"]),
        eval_strategy="no",
        save_strategy="no",
        logging_strategy="steps",
        logging_steps=50,
        fp16=torch.cuda.is_available(),
        gradient_checkpointing=gradient_checkpointing,
        report_to="none",
        seed=seed,
        data_seed=seed,
    )


def train_text(config: dict, data_root: Path, output_root: Path, epochs: int) -> dict:
    import torch
    import transformers
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
    )

    from ml.training.train_iemocap_text import seed_everything

    seed, labels, settings = config["seed"], config["labels"], config["text"]
    seed_everything(seed)
    dataset = load_full_dataset(data_root, config["task"])
    tokenizer = AutoTokenizer.from_pretrained(settings["model_name"])
    tokenized = dataset.map(
        lambda batch: tokenizer(
            batch[settings["input_field"]], truncation=True, max_length=settings["max_length"]
        ),
        batched=True,
        desc="Tokenizing final context-text dataset",
    )
    run_dir = output_root / config["experiment_name"] / "text"
    run_dir.mkdir(parents=True, exist_ok=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        settings["model_name"],
        num_labels=len(labels),
        id2label=dict(enumerate(labels)),
        label2id={label: index for index, label in enumerate(labels)},
        dtype=torch.float32,
    )
    trainer = Trainer(
        model=model,
        args=_arguments(run_dir, settings, epochs, seed),
        train_dataset=tokenized,
        processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
    )
    result = trainer.train()
    model_dir = run_dir / "model"
    trainer.save_model(model_dir)
    tokenizer.save_pretrained(model_dir)
    return _write_manifest(
        run_dir, config, "text", settings["model_name"], epochs, result.metrics, torch, transformers
    )


def train_audio(config: dict, data_root: Path, audio_root: Path, output_root: Path, epochs: int) -> dict:
    import torch
    import transformers
    from transformers import (
        AutoFeatureExtractor,
        AutoModelForAudioClassification,
        Trainer,
    )

    from ml.training.train_iemocap_audio import (
        AudioCollator,
        AudioDataset,
        audio_audit,
        seed_everything,
    )

    seed, labels, settings = config["seed"], config["labels"], config["audio"]
    seed_everything(seed)
    dataset = load_full_dataset(data_root, config["task"])
    audit = audio_audit(dataset, audio_root, settings["maximum_duration_seconds"])
    extractor = AutoFeatureExtractor.from_pretrained(settings["model_name"])
    if extractor.sampling_rate != settings["sampling_rate"]:
        raise ValueError("Configured sampling rate differs from feature extractor")
    training_dataset = AudioDataset(
        dataset,
        audio_root,
        settings["sampling_rate"],
        round(settings["maximum_duration_seconds"] * settings["sampling_rate"]),
    )
    run_dir = output_root / config["experiment_name"] / "audio"
    run_dir.mkdir(parents=True, exist_ok=True)
    model = AutoModelForAudioClassification.from_pretrained(
        settings["model_name"],
        num_labels=len(labels),
        id2label=dict(enumerate(labels)),
        label2id={label: index for index, label in enumerate(labels)},
        dtype=torch.float32,
    )
    if settings["freeze_feature_encoder"]:
        if hasattr(model, "freeze_feature_encoder"):
            model.freeze_feature_encoder()
        else:
            model.wav2vec2.feature_extractor._freeze_parameters()
    trainer = Trainer(
        model=model,
        args=_arguments(run_dir, settings, epochs, seed, settings["gradient_checkpointing"]),
        train_dataset=training_dataset,
        processing_class=extractor,
        data_collator=AudioCollator(extractor),
    )
    result = trainer.train()
    model_dir = run_dir / "model"
    trainer.save_model(model_dir)
    extractor.save_pretrained(model_dir)
    manifest = _write_manifest(
        run_dir, config, "audio", settings["model_name"], epochs, result.metrics, torch, transformers
    )
    manifest["audio_audit"] = audit
    (run_dir / "training_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def _write_manifest(
    run_dir: Path, config: dict, modality: str, base_model: str, epochs: int, metrics: dict, torch, transformers
) -> dict:
    manifest = {
        "experiment": config["experiment_name"],
        "modality": modality,
        "purpose": "final_full_data_artifact_not_an_evaluation_run",
        "created_at": datetime.now(UTC).isoformat(),
        "seed": config["seed"],
        "base_model": base_model,
        "labels": config["labels"],
        "training_examples": 5531,
        "epochs": epochs,
        "train_metrics": metrics,
        "calibration": config["calibration"],
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        },
    }
    (run_dir / "training_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--modality", choices=("text", "audio"), required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--epochs", type=int, required=True)
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("--epochs must be positive")
    configuration = json.loads(args.config.read_text(encoding="utf-8"))
    if args.modality == "text":
        output = train_text(configuration, args.data_root, args.output_root, args.epochs)
    else:
        if args.audio_root is None:
            parser.error("--audio-root is required for audio")
        output = train_audio(
            configuration, args.data_root, args.audio_root, args.output_root, args.epochs
        )
    print(json.dumps(output, indent=2))
