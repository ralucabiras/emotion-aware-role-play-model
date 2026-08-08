from ml.evaluation.paired_cluster_bootstrap import compare, dialogue_id, metrics_from_confusion


def test_dialogue_id_and_confusion_metrics() -> None:
    assert dialogue_id("Ses01F_impro01_F012") == "Ses01F_impro01"
    metrics = metrics_from_confusion(__import__("numpy").array([[2, 0], [1, 1]]))
    assert metrics["accuracy"] == 0.75
    assert 0 < metrics["macro_f1"] < 1


def test_paired_dialogue_bootstrap_detects_consistent_improvement() -> None:
    grouped = {
        f"dialogue-{index}": [
            {"id": f"u-{index}", "expected": "positive", "baseline": "negative", "context": "positive"},
            {"id": f"v-{index}", "expected": "negative", "baseline": "positive", "context": "negative"},
        ]
        for index in range(6)
    }

    result = compare(["negative", "positive"], grouped, iterations=200, seed=7)

    assert result["dialogues"] == 6
    assert result["utterances"] == 12
    assert result["observed"]["macro_f1"]["difference"] == 1.0
    assert result["observed"]["macro_f1"]["lower_95"] == 1.0
    assert result["observed"]["macro_f1"]["probability_improvement"] == 1.0
