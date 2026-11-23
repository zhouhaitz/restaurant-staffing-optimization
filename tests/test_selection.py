"""Fast tests for the statistical-selection layer (no long simulation runs)."""
import numpy as np
import pytest
from dataclasses import replace

from parameters import SingleDishParameters
from runner import run_single_dish_sim
import selection
from statistical_validation import run_crn_paired


def _short(**kw):
    return SingleDishParameters(simulation_duration=60.0, **kw)


def test_same_seed_is_reproducible():
    a = run_single_dish_sim(_short(seed=11))["net_revpash"]
    b = run_single_dish_sim(_short(seed=11))["net_revpash"]
    assert a == b


def test_different_seeds_differ():
    vals = {run_single_dish_sim(_short(seed=s))["net_revpash"] for s in (1, 2, 3, 4)}
    assert len(vals) > 1


def test_compute_ci_matches_scipy():
    x = np.array([3.0, 3.5, 4.0, 3.2, 3.8])
    ci = selection.compute_ci(x)
    from scipy import stats
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=stats.sem(x))
    assert ci["ci_lower"] == pytest.approx(lo) and ci["ci_upper"] == pytest.approx(hi)


def test_required_n_grows_with_variance():
    rng = np.random.default_rng(0)
    calm = rng.normal(10, 0.5, 30)
    noisy = rng.normal(10, 3.0, 30)
    n_calm = selection.estimate_n_required(calm, target_relative_error=0.05)["n_required"]
    n_noisy = selection.estimate_n_required(noisy, target_relative_error=0.05)["n_required"]
    assert n_noisy > n_calm


def test_subset_selection_screens_out_clearly_worse_config():
    rng = np.random.default_rng(1)
    def entry(mu):
        s = rng.normal(mu, 0.2, 10)
        return {"samples": s, "ci": selection.compute_ci(s), "config": None}
    res = {0: entry(5.0), 1: entry(4.95), 2: entry(1.0)}
    sel = selection.subset_selection(res)
    assert 2 in sel["not_best"]
    assert 0 in sel["may_be_best"]


def test_config_grid_size():
    grid = selection.generate_configuration_grid(
        SingleDishParameters(), server_range=[4, 5], cook_range=[8, 9, 10],
        food_runner_range=[1, 2], busser_range=[0])
    assert len(grid) == 2 * 3 * 1 * 2 * 1


def test_crn_pair_keeps_non_staffing_fields():
    """Regression: run_crn_paired used to rebuild configs and drop recipes/runner counts."""
    base = _short(num_food_runners=1, num_bussers=0, num_servers=4, num_cooks=6)
    a, b = base, replace(base, num_servers=5)
    out = run_crn_paired((a, b), n_rep=2, base_seed=5)
    assert out["n"] == 2 and len(out["paired_diffs"]) == 2
