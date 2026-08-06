"""Fine-tune a text classifier on one speaker-independent IEMOCAP fold."""

import argparse
import json
import math
import os
import platform
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_everything(seed: int) -> None:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def calculate_class_weights(labels: list[int], class_count: int, mode: str, maximum: float) -> list[float]:
    if mode == "none":
        return [1.0] * class_count
    if mode != "balanced_clipped":
        raise ValueError(f"Unsupported class weighting mode: {mode}")
    counts = Counter(labels)
    if missing := sorted(set(range(class_count)) - counts.keys()):
        raise ValueError(f"Training split is missing label ids: {missing}")
    total = len(labels)
    return [min(maximum, total / (class_count * counts[index])) for index in range(class_count)]


def run(config_path: Path, data_root: Path, output_root: Path, fold: int, seed: int) -> dict:
    import datasets
    import torch
    import transformers
    from datasets import load_from_disk
    from torch.nn import CrossEntropyLoss
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        EarlyStoppingCallback,
        Trainer,
        TrainingArguments,
    )

    from ml.evaluation.metrics import classification_metrics, per_class_metrics, softmax
    from ml.training.train_meld import plot_confusion

    config = load_config(config_path)
    if fold not in range(1, 6):
        raise ValueError("fold must be between 1 and 5")
    seed_everything(seed)
    labels = config["labels"]
    id2label = dict(enumerate(labels))
    label2id = {label: index for index, label in id2label.items()}
    dataset_path = data_root / config["task"] / f"fold-{fold}" / "dataset"
    dataset = load_from_disk(str(dataset_path))
    tokenizer = AutoTokenizer.from_pretrained(config["model_name"])

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=config["max_length"])

    tokenized = dataset.map(tokenize, batched=True, desc=f"Tokenizing IEMOCAP fold {fold}")
    run_dir = output_root / config["experiment_name"] / f"fold-{fold}"
    run_dir.mkdir(parents=True, exist_ok=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        config["model_name"],
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
        dtype=torch.float32,
    )
    trainable_dtypes = {parameter.dtype for parameter in model.parameters() if parameter.requires_grad}
    if trainable_dtypes != {torch.float32}:
        raise RuntimeError(f"Expected FP32 trainable weights, found: {trainable_dtypes}")

    class_weights = calculate_class_weights(
        dataset["train"]["label"],
        len(labels),
        config["class_weighting"],
        float(config.get("maximum_class_weight", 10.0)),
    )

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            labels_tensor = inputs.pop("labels")
            outputs = model(**inputs)
            weights = torch.tensor(class_weights, dtype=outputs.logits.dtype, device=outputs.logits.device)
            loss = CrossEntropyLoss(weight=weights)(outputs.logits, labels_tensor)
            return (loss, outputs) if return_outputs else loss

    def compute_metrics(prediction):
        return classification_metrics(prediction.predictions, prediction.label_ids)

    batches_per_epoch = math.ceil(len(dataset["train"]) / config["train_batch_size"])
    optimizer_steps = math.ceil(batches_per_epoch / config["gradient_accumulation_steps"]) * config["epochs"]
    warmup_steps = round(optimizer_steps * config["warmup_ratio"])
    use_fp16 = torch.cuda.is_available()
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
        fp16=use_fp16,
        report_to="none",
        seed=seed,
        data_seed=seed,
    )
    trainer = WeightedTrainer(
        model=model,
        args=arguments,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=config["early_stopping_patience"])],
    )
    train_result = trainer.train()
    trainer.remove_callback(EarlyStoppingCallback)
    validation = trainer.evaluate(tokenized["validation"], metric_key_prefix="validation")
    test_output = trainer.predict(tokenized["test"], metric_key_prefix="test")
    probabilities = softmax(test_output.predictions)
    predictions = probabilities.argmax(axis=1)
    model_dir = run_dir / "model"
    trainer.save_model(model_dir)
    tokenizer.save_pretrained(model_dir)
    export = {
        "experiment": config["experiment_name"],
        "task": config["task"],
        "fold": fold,
        "seed": seed,
        "created_at": datetime.now(UTC).isoformat(),
        "base_model": config["model_name"],
        "labels": labels,
        "class_weighting": config["class_weighting"],
        "class_weights": dict(zip(labels, class_weights, strict=True)),
        "split_sessions": {
            split: sorted(set(dataset[split]["session"])) for split in ("train", "validation", "test")
        },
        "train_metrics": train_result.metrics,
        "validation_metrics": validation,
        "test_metrics": test_output.metrics,
        "test_per_class": per_class_metrics(test_output.label_ids, predictions, labels),
        "log_history": trainer.state.log_history,
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "datasets": datasets.__version__,
            "precision": "fp16-mixed" if use_fp16 else "fp32",
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        },
    }
    (run_dir / "metrics.json").write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
    (model_dir / "affectlab_metadata.json").write_text(
        json.dumps({"labels": labels, "task": config["task"], "fold": fold, "seed": seed}, indent=2) + "\n",
        encoding="utf-8",
    )
    with (run_dir / "test_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for item_id, expected, predicted, probability in zip(
            dataset["test"]["id"], test_output.label_ids, predictions, probabilities, strict=True
        ):
            handle.write(
                json.dumps(
                    {
                        "id": item_id,
                        "expected": labels[int(expected)],
                        "predicted": labels[int(predicted)],
                        "confidence": float(probability.max()),
                        "probabilities": {label: float(probability[index]) for index, label in enumerate(labels)},
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
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    print(json.dumps(run(args.config, args.data_root, args.output_root, args.fold, args.seed), indent=2))
