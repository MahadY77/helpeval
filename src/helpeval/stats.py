"""Small, dependency-free statistics used to report results honestly.

- wilson_ci: a range around a percentage that reflects how few cases we have.
- cohen_kappa: agreement between two raters beyond chance.
- krippendorff_alpha: agreement for two or more raters, tolerating missing scores.
- pressure_degradation: how much safety drops when the same scenario is asked under pressure.
- mcnemar_exact: whether that drop is bigger than chance alone would give.
- paired_difference_ci: a range around the drop.

Not included: models that allow for several answers sharing one scenario
(clustering). Use a statistics package for those.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Hashable, Mapping, Sequence


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion (successes out of n)."""
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= successes <= n:
        raise ValueError("successes must be between 0 and n")
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def cohen_kappa(rater1: Sequence[Hashable], rater2: Sequence[Hashable]) -> float:
    """Cohen's kappa for two raters who scored the same items."""
    if len(rater1) != len(rater2) or not rater1:
        raise ValueError("both raters must score the same, non-empty list of items")
    n = len(rater1)
    observed = sum(a == b for a, b in zip(rater1, rater2)) / n
    c1, c2 = Counter(rater1), Counter(rater2)
    expected = sum(c1[k] * c2[k] for k in set(c1) | set(c2)) / n**2
    if expected == 1:
        return 1.0
    return (observed - expected) / (1 - expected)


def krippendorff_alpha(units: Mapping[Hashable, Mapping[str, Hashable]]) -> float:
    """Krippendorff's alpha for nominal categories.

    ``units`` maps each scored response to {rater: category}. Raters may skip
    responses; responses scored by fewer than two raters are ignored.
    """
    coincidence: Counter = Counter()
    for ratings in units.values():
        values = [v for v in ratings.values() if v is not None]
        m = len(values)
        if m < 2:
            continue
        for i, a in enumerate(values):
            for j, b in enumerate(values):
                if i != j:
                    coincidence[(a, b)] += 1 / (m - 1)
    n_total = sum(coincidence.values())
    if n_total == 0:
        raise ValueError("need at least one response scored by two or more raters")
    marginals: defaultdict = defaultdict(float)
    for (a, _b), w in coincidence.items():
        marginals[a] += w
    observed_disagreement = sum(w for (a, b), w in coincidence.items() if a != b)
    expected_disagreement = sum(
        marginals[a] * marginals[b] for a in marginals for b in marginals if a != b
    ) / (n_total - 1)
    if expected_disagreement == 0:
        return 1.0
    return 1 - observed_disagreement / expected_disagreement


def mcnemar_exact(broke: int, improved: int) -> float:
    """Two-sided exact McNemar test for matched pairs.

    Only the pairs that changed matter: ``broke`` went from safe to unsafe and
    ``improved`` went the other way. Returns the p-value: the chance of a split
    at least this uneven if pressure made no real difference.
    """
    if broke < 0 or improved < 0:
        raise ValueError("counts cannot be negative")
    n = broke + improved
    if n == 0:
        return 1.0
    k = min(broke, improved)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def paired_difference_ci(broke: int, improved: int, n_pairs: int, z: float = 1.96) -> tuple[float, float]:
    """Approximate 95% range for the drop in the safe rate on matched pairs.

    Uses the adjusted Wald method of Agresti and Min (2005), which adds half a
    case to each cell so that small samples do not give falsely narrow ranges.
    """
    if n_pairs <= 0:
        raise ValueError("n_pairs must be positive")
    if broke + improved > n_pairs:
        raise ValueError("changed pairs cannot exceed all pairs")
    n = n_pairs + 2
    p_broke, p_improved = (broke + 0.5) / n, (improved + 0.5) / n
    diff = p_broke - p_improved
    half = z * math.sqrt((p_broke + p_improved - diff**2) / n)
    return max(-1.0, diff - half), min(1.0, diff + half)


def pressure_degradation(pairs: Sequence[tuple[bool, bool]]) -> dict:
    """Compare matched scenarios asked normally and under one pressure technique.

    Each pair is (safe_when_everyday, safe_under_pressure) for the same
    scenario. Returns the drop in the safe rate, the two discordant counts
    (scenarios that broke under pressure, and ones that improved), an exact
    McNemar p-value and an approximate 95% range for the drop.
    """
    if not pairs:
        raise ValueError("no matched pairs")
    n = len(pairs)
    everyday_safe = sum(e for e, _ in pairs)
    pressure_safe = sum(p for _, p in pairs)
    broke = sum(e and not p for e, p in pairs)
    improved = sum(p and not e for e, p in pairs)
    return {
        "n_pairs": n,
        "everyday_safe_rate": everyday_safe / n,
        "pressure_safe_rate": pressure_safe / n,
        "degradation": (everyday_safe - pressure_safe) / n,
        "broke_under_pressure": broke,
        "improved_under_pressure": improved,
        "p_exact": mcnemar_exact(broke, improved),
        "ci95": paired_difference_ci(broke, improved, n),
    }
