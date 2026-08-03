from ml.preprocessing.meld import LABELS, normalize_example


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
