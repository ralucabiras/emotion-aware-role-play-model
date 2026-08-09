import pytest
from ml.training.smoke_iemocap_final import balanced_rows


def test_balanced_rows_selects_declared_count_per_label() -> None:
    rows = [
        {"id": f"{label}-{index}", "label": label}
        for index in range(4)
        for label in range(2)
    ]

    selected = balanced_rows(rows, ["negative", "positive"], 3)

    assert len(selected) == 6
    assert sum(row["label"] == 0 for row in selected) == 3
    assert sum(row["label"] == 1 for row in selected) == 3


def test_balanced_rows_rejects_insufficient_class_examples() -> None:
    with pytest.raises(ValueError, match="balanced smoke sample"):
        balanced_rows([{"id": "only", "label": 0}], ["negative", "positive"], 1)
