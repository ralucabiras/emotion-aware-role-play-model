"""Descriptive analysis helpers frozen for the v1.1 researcher dashboard."""

import hashlib
import math
import random
import statistics
from collections.abc import Iterable


def percentile(values: Iterable[float], probability: float) -> float | None:
    """Linear-interpolated percentile using index ``(n - 1) * probability``."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def describe(values: Iterable[float]) -> dict[str, float | int | None]:
    """Return available-case descriptive statistics without imputing values."""
    observed = [float(value) for value in values]
    return {
        "n": len(observed),
        "mean": statistics.fmean(observed) if observed else None,
        "sd": statistics.stdev(observed) if len(observed) > 1 else None,
        "median": statistics.median(observed) if observed else None,
        "q1": percentile(observed, 0.25),
        "q3": percentile(observed, 0.75),
        "min": min(observed) if observed else None,
        "max": max(observed) if observed else None,
    }


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    """Two-sided Wilson score interval for a binomial proportion."""
    if total <= 0:
        return None
    proportion = successes / total
    denominator = 1 + z**2 / total
    centre = (proportion + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z**2 / (4 * total**2)) / denominator
    return [max(0.0, centre - margin), min(1.0, centre + margin)]


def cluster_bootstrap_median_interval(
    observations: Iterable[tuple[str, float]],
    *,
    seed_label: str,
    iterations: int = 5_000,
) -> list[float] | None:
    """Percentile 95% CI for the median, resampling participant clusters."""
    clusters: dict[str, list[float]] = {}
    for participant_id, value in observations:
        clusters.setdefault(participant_id, []).append(float(value))
    cluster_ids = sorted(clusters)
    if not cluster_ids:
        return None
    seed = int.from_bytes(hashlib.sha256(seed_label.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    estimates = []
    for _ in range(iterations):
        sample = [rng.choice(cluster_ids) for _ in cluster_ids]
        values = [value for participant_id in sample for value in clusters[participant_id]]
        estimates.append(statistics.median(values))
    return [percentile(estimates, 0.025), percentile(estimates, 0.975)]
