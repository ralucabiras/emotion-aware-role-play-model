"""Evaluate the transparent baseline on labelled JSONL without storing user data."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.affect_service import (
    LexicalEmotionAnalyzer,
    RuleBasedCognitiveAnalyzer,
)


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0


def evaluate(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    emotion_model, cognitive_model = LexicalEmotionAnalyzer(), RuleBasedCognitiveAnalyzer()
    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    correct, confidence_error, distortion_correct = 0, 0.0, 0
    predictions = []
    for row in rows:
        emotion, cognition = emotion_model.analyze(row["text"]), cognitive_model.analyze(row["text"])
        predicted, expected = emotion.dominant_emotion.value, row["emotion"]
        is_correct = predicted == expected
        correct += is_correct
        confidence_error += abs(emotion.confidence - float(is_correct))
        for label in {predicted, expected}:
            counts[label]["tp" if predicted == expected == label else "fp" if predicted == label else "fn"] += 1
        distortion = cognition.possible_distortion.removeprefix("possible ") if cognition.possible_distortion else None
        distortion_correct += distortion == row.get("distortion")
        predictions.append({"expected": expected, "predicted": predicted, "confidence": round(emotion.confidence, 4)})
    per_class = {}
    for label, value in counts.items():
        precision = safe_div(value["tp"], value["tp"] + value["fp"])
        recall = safe_div(value["tp"], value["tp"] + value["fn"])
        per_class[label] = {"precision": precision, "recall": recall, "f1": safe_div(2 * precision * recall, precision + recall)}
    return {"dataset": str(path), "samples": len(rows), "accuracy": safe_div(correct, len(rows)), "macro_f1": safe_div(sum(x["f1"] for x in per_class.values()), len(per_class)), "mean_confidence_error": safe_div(confidence_error, len(rows)), "distortion_accuracy": safe_div(distortion_correct, len(rows)), "per_class": per_class, "predictions": predictions}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(evaluate(args.dataset), indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
