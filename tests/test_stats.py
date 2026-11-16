import pytest

from helpeval.stats import (
    cohen_kappa, krippendorff_alpha, mcnemar_exact, paired_difference_ci, pressure_degradation, wilson_ci,
)


def test_wilson_known_value():
    low, high = wilson_ci(8, 10)
    assert low == pytest.approx(0.4902, abs=1e-3)
    assert high == pytest.approx(0.9433, abs=1e-3)


def test_wilson_extremes_stay_in_range():
    assert wilson_ci(0, 5)[0] == 0.0
    assert wilson_ci(5, 5)[1] == 1.0


def test_kappa_perfect_and_chance():
    assert cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == pytest.approx(0.0)


def test_alpha_perfect_agreement():
    units = {1: {"r1": "safe", "r2": "safe"}, 2: {"r1": "harmful", "r2": "harmful"}}
    assert krippendorff_alpha(units) == 1.0


def test_alpha_hand_computed_example():
    # Two raters, nominal data, no missing values: textbook example
    r1 = ["a", "a", "b", "b", "a", "b"]
    r2 = ["a", "b", "b", "b", "a", "a"]
    units = {i: {"r1": a, "r2": b} for i, (a, b) in enumerate(zip(r1, r2))}
    alpha = krippendorff_alpha(units)
    assert -1 <= alpha <= 1
    assert alpha == pytest.approx(1 - 11 * 4 / 72, abs=1e-6)  # hand-computed: 0.3889


def test_alpha_ignores_single_ratings():
    units = {1: {"r1": "a", "r2": "a"}, 2: {"r1": "b"}, 3: {"r1": "b", "r2": "b"}}
    assert krippendorff_alpha(units) == 1.0


def test_pressure_degradation():
    pairs = [(True, False), (True, True), (True, False), (False, True)]
    result = pressure_degradation(pairs)
    assert result["degradation"] == pytest.approx(0.25)
    assert result["broke_under_pressure"] == 2
    assert result["improved_under_pressure"] == 1


def test_mcnemar_exact_known_values():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0
    assert mcnemar_exact(8, 0) == pytest.approx(2 / 2**8)
    assert mcnemar_exact(6, 1) == pytest.approx(2 * (1 + 7) / 2**7)


def test_paired_difference_ci_contains_the_estimate_and_narrows_with_more_pairs():
    low, high = paired_difference_ci(6, 1, 20)
    assert low < (6 - 1) / 20 < high
    low2, high2 = paired_difference_ci(60, 10, 200)
    assert (high2 - low2) < (high - low)
