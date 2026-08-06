from ml.preprocessing.iemocap import fold_sessions, parse_annotation_line, parse_transcript_line
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


def test_iemocap_annotation_parsing_preserves_dimensions_and_media_reference() -> None:
    result = parse_annotation_line(
        "[6.2901 - 8.2357]\tSes01F_impro01_F000\tneu\t[2.5000, 3.0000, 2.0000]"
    )

    assert result is not None
    assert result["session"] == 1
    assert result["speaker"] == "Ses01F"
    assert result["dialogue_id"] == "Ses01F_impro01"
    assert result["is_improvised"] is True
    assert result["source_label"] == "neu"
    assert result["arousal"] == 3.0
    assert result["audio_archive_member"].endswith("Ses01F_impro01_F000.wav")


def test_iemocap_transcript_and_session_folds() -> None:
    assert parse_transcript_line("Ses01F_impro01_F000 [006.2901-008.2357]: Excuse me.") == (
        "Ses01F_impro01_F000",
        "Excuse me.",
    )
    assert fold_sessions(5) == {"train": [1, 2, 3], "validation": [4], "test": [5]}
    assert fold_sessions(1) == {"train": [2, 3, 4], "validation": [5], "test": [1]}
