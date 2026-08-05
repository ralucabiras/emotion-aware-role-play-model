"""Download and validate MELD's official text annotations."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

MELD_BASE = "https://raw.githubusercontent.com/declare-lab/MELD/master/data/MELD"
FILES = {
    "train": f"{MELD_BASE}/train_sent_emo.csv",
    "validation": f"{MELD_BASE}/dev_sent_emo.csv",
    "test": f"{MELD_BASE}/test_sent_emo.csv",
}
LABELS = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]


def normalize_example(example: dict, split: str) -> dict:
    text = str(example["Utterance"]).strip()
    emotion = str(example["Emotion"]).strip().lower()
    dialogue_id = int(example["Dialogue_ID"])
    utterance_id = int(example["Utterance_ID"])
    if not text:
        raise ValueError(f"Empty utterance in {split}:{dialogue_id}:{utterance_id}")
    if emotion not in LABELS:
        raise ValueError(f"Unknown MELD emotion: {emotion}")
    return {
        "id": f"{split}:{dialogue_id}:{utterance_id}",
        "text": text,
        "label_name": emotion,
        "label": LABELS.index(emotion),
        "dialogue_id": dialogue_id,
        "utterance_id": utterance_id,
        "speaker": str(example["Speaker"]),
    }


def find_dialogue_overlaps(dialogue_signatures: dict[str, dict[str, int]]) -> list[dict]:
    """Describe exact cross-split duplicates without changing official MELD splits."""
    overlaps = []
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        for signature in sorted(dialogue_signatures[left].keys() & dialogue_signatures[right].keys()):
            overlaps.append(
                {
                    "left_split": left,
                    "left_dialogue_id": dialogue_signatures[left][signature],
                    "right_split": right,
                    "right_dialogue_id": dialogue_signatures[right][signature],
                    "sha256": signature,
                }
            )
    return overlaps


def prepare(output_dir: Path):
    from datasets import Dataset, DatasetDict, load_dataset

    raw = load_dataset("csv", data_files=FILES)
    columns = ["Utterance", "Speaker", "Emotion", "Dialogue_ID", "Utterance_ID"]
    missing = {split: sorted(set(columns) - set(dataset.column_names)) for split, dataset in raw.items()}
    if any(missing.values()):
        raise ValueError(f"MELD schema changed; missing columns: {missing}")
    cleaned = DatasetDict()
    split_dialogues: dict[str, set[int]] = {}
    dialogue_signatures: dict[str, dict[str, int]] = {}
    for split, dataset in raw.items():
        normalized = [normalize_example(row, split) for row in dataset]
        cleaned[split] = Dataset.from_list(normalized)
        split_dialogues[split] = {row["dialogue_id"] for row in normalized}
        grouped: dict[int, list[tuple[int, str]]] = {}
        for row in normalized:
            grouped.setdefault(row["dialogue_id"], []).append((row["utterance_id"], row["text"].lower()))
        dialogue_signatures[split] = {
            hashlib.sha256("\n".join(text for _, text in sorted(turns)).encode()).hexdigest(): dialogue_id
            for dialogue_id, turns in grouped.items()
        }
    overlaps = find_dialogue_overlaps(dialogue_signatures)
    output_dir.mkdir(parents=True, exist_ok=True)
    cleaned.save_to_disk(str(output_dir / "dataset"))
    manifest = {
        "dataset": "MELD",
        "source_files": FILES,
        "labels": LABELS,
        "integrity": {
            "official_splits_preserved": True,
            "exact_cross_split_dialogue_overlaps": overlaps,
            "warning": (
                "MELD's official splits contain exact duplicate dialogue content. "
                "The duplicates are retained for benchmark comparability and disclosed here."
                if overlaps
                else None
            ),
        },
        "splits": {
            split: {
                "examples": len(dataset),
                "dialogues": len(split_dialogues[split]),
                "label_counts": dict(sorted(Counter(dataset["label_name"]).items())),
                "fingerprint": dataset._fingerprint,
            }
            for split, dataset in cleaned.items()
        },
    }
    encoded = json.dumps(manifest, sort_keys=True).encode()
    manifest["manifest_sha256"] = hashlib.sha256(encoded).hexdigest()
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return cleaned, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    _, result = prepare(args.output_dir)
    print(json.dumps(result, indent=2))
