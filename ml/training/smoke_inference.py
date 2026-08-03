"""Verify an exported checkpoint and its AffectLab label mapping."""

import argparse
import json
from pathlib import Path


def predict(model_dir: Path, texts: list[str]) -> list[dict]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    metadata = json.loads((model_dir / "affectlab_metadata.json").read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).eval()
    encoded = tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        probabilities = model(**encoded).logits.softmax(dim=-1)
    output = []
    for text, row in zip(texts, probabilities, strict=True):
        index = int(row.argmax())
        meld_label = metadata["labels"][index]
        output.append({"text": text, "meld_label": meld_label, "affectlab_label": metadata["affectlab_mapping"][meld_label], "confidence": float(row[index])})
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("texts", nargs="+")
    args = parser.parse_args()
    print(json.dumps(predict(args.model_dir, args.texts), indent=2))
