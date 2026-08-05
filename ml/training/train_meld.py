"""Fine-tune and evaluate a text classifier on prepared MELD splits."""

import argparse
import json
import os
import platform
import random
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ml.evaluation.metrics import classification_metrics, per_class_metrics, softmax


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_everything(seed: int) -> None:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def plot_confusion(labels, predictions, label_names: list[str], output: Path) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import confusion_matrix

    matrix = confusion_matrix(labels, predictions, labels=range(len(label_names)), normalize="true")
    figure, axis = plt.subplots(figsize=(9, 7))
    sns.heatmap(matrix, annot=True, fmt=".2f", cmap="Blues", xticklabels=label_names, yticklabels=label_names, ax=axis)
    axis.set(xlabel="Predicted", ylabel="True", title="MELD normalized confusion matrix")
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def run(config_path: Path, data_dir: Path, output_root: Path, seed: int) -> dict:
    import torch
    import transformers
    from datasets import load_from_disk
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        EarlyStoppingCallback,
        Trainer,
        TrainingArguments,
    )

    config = load_config(config_path)
    seed_everything(seed)
    labels = config["labels"]
    id2label = {index: label for index, label in enumerate(labels)}
    label2id = {label: index for index, label in id2label.items()}
    dataset = load_from_disk(str(data_dir / "dataset"))
    tokenizer = AutoTokenizer.from_pretrained(config["model_name"])

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=config["max_length"])

    tokenized = dataset.map(tokenize, batched=True, desc="Tokenizing MELD")
    run_dir = output_root / f"seed-{seed}"
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
        raise RuntimeError(
            "Mixed-precision training requires FP32 trainable weights; "
            f"found {sorted(str(dtype) for dtype in trainable_dtypes)}"
        )

    def compute_metrics(prediction):
        return classification_metrics(prediction.predictions, prediction.label_ids)

    use_fp16 = bool(config["fp16"] and torch.cuda.is_available())
    arguments = TrainingArguments(
        output_dir=str(run_dir / "checkpoints"),
        learning_rate=config["learning_rate"],
        per_device_train_batch_size=config["train_batch_size"],
        per_device_eval_batch_size=config["eval_batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation_steps"],
        num_train_epochs=config["epochs"],
        weight_decay=config["weight_decay"],
        warmup_ratio=config["warmup_ratio"],
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
    trainer = Trainer(
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
    validation = trainer.evaluate(tokenized["validation"], metric_key_prefix="validation")
    test_output = trainer.predict(tokenized["test"], metric_key_prefix="test")
    probabilities = softmax(test_output.predictions)
    predictions = probabilities.argmax(axis=1)
    model_dir = run_dir / "model"
    trainer.save_model(model_dir)
    tokenizer.save_pretrained(model_dir)
    export = {
        "experiment": config["experiment_name"],
        "seed": seed,
        "created_at": datetime.now(UTC).isoformat(),
        "base_model": config["model_name"],
        "labels": labels,
        "affectlab_mapping": config["affectlab_mapping"],
        "train_metrics": train_result.metrics,
        "validation_metrics": validation,
        "test_metrics": test_output.metrics,
        "test_per_class": per_class_metrics(test_output.label_ids, predictions, labels),
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "precision": "fp16-mixed" if use_fp16 else "fp32",
            "cuda_available": torch.cuda.is_available(),
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        },
    }
    (run_dir / "metrics.json").write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
    (model_dir / "affectlab_metadata.json").write_text(
        json.dumps({"labels": labels, "affectlab_mapping": config["affectlab_mapping"], "seed": seed}, indent=2) + "\n",
        encoding="utf-8",
    )
    with (run_dir / "test_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for item_id, expected, predicted, confidence in zip(
            dataset["test"]["id"], test_output.label_ids, predictions, probabilities.max(axis=1), strict=True
        ):
            handle.write(json.dumps({"id": item_id, "expected": labels[int(expected)], "predicted": labels[int(predicted)], "confidence": float(confidence)}) + "\n")
    plot_confusion(test_output.label_ids, predictions, labels, run_dir / "confusion_matrix.png")
    return export


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    print(json.dumps(run(args.config, args.data_dir, args.output_dir, args.seed), indent=2))
