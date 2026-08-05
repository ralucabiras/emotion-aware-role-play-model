from ml.preprocessing.meld import LABELS, find_dialogue_overlaps, normalize_example


def test_meld_normalization_preserves_dialogue_identity() -> None:
    result = normalize_example(
        {
            "Utterance": "  I am worried. ",
            "Emotion": "fear",
            "Dialogue_ID": "12",
            "Utterance_ID": "3",
            "Speaker": "Speaker",
        },
        "train",
    )
    assert result["id"] == "train:12:3"
    assert result["text"] == "I am worried."
    assert result["label"] == LABELS.index("fear")


def test_meld_cross_split_duplicates_are_audited() -> None:
    result = find_dialogue_overlaps(
        {
            "train": {"duplicate": 1, "train-only": 2},
            "validation": {"validation-only": 3},
            "test": {"duplicate": 4},
        }
    )

    assert result == [
        {
            "left_split": "train",
            "left_dialogue_id": 1,
            "right_split": "test",
            "right_dialogue_id": 4,
            "sha256": "duplicate",
        }
    ]
