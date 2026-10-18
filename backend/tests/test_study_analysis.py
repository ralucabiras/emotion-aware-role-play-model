import pytest

from app.services.study_analysis import (
    cluster_bootstrap_median_interval,
    describe,
    wilson_interval,
)


def test_descriptive_statistics_use_available_values_and_sample_sd():
    summary = describe([1, 2, 3, 4])
    assert summary == {
        "n": 4, "mean": 2.5, "sd": pytest.approx(1.2909944487),
        "median": 2.5, "q1": 1.75, "q3": 3.25, "min": 1.0, "max": 4.0,
    }
    assert describe([]) == {
        "n": 0, "mean": None, "sd": None, "median": None,
        "q1": None, "q3": None, "min": None, "max": None,
    }


def test_wilson_interval_and_cluster_bootstrap_are_deterministic():
    wilson = wilson_interval(12, 15)
    assert wilson == pytest.approx([0.5481455128, 0.9295245065])
    observations = [("participant-a", 1), ("participant-a", 2), ("participant-b", -1)]
    first = cluster_bootstrap_median_interval(observations, seed_label="fixed", iterations=500)
    second = cluster_bootstrap_median_interval(observations, seed_label="fixed", iterations=500)
    assert first == second
    assert first[0] <= 1 <= first[1]
