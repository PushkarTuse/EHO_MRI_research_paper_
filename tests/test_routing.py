"""Meaningful routing invariants and recovered-source defect checks."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import routing
import replay_snippets


def test_validators_reject_omissions_duplicates_and_capacity_violation():
    assert routing.validate_tsp([0, 1, 2], 3)["valid"]
    assert not routing.validate_tsp([0, 1, 1], 3)["valid"]
    assert not routing.validate_tsp([0, 1], 3)["valid"]
    demands = np.array([0, 3, 4, 2])
    assert routing.validate_vrp([[1, 3], [2]], demands, 5, 2)["valid"]
    assert not routing.validate_vrp([[1, 2], [3]], demands, 5, 2)["valid"]
    assert not routing.validate_vrp([[1], [2]], demands, 5, 2)["valid"]
    assert not routing.validate_vrp([[1, 3], [2, 3]], demands, 5, 2)["valid"]
    assert not routing.validate_vrp([[0], [1, 3], [2]], demands, 5, 3)["valid"]


def test_next_fit_preserves_every_customer_and_rejects_fleet_overflow():
    demands = np.array([0, 4, 4, 4])
    routes = routing.split_permutation([3, 1, 2], demands, 5, 3)
    assert routes == [[3], [1], [2]]
    assert routing.validate_vrp(routes, demands, 5, 3)["valid"]
    assert routing.split_permutation([3, 1, 2], demands, 5, 2) is None
    with pytest.raises(ValueError): routing.split_permutation([1, 1, 2], demands, 5, 3)


@pytest.mark.parametrize("method", ["EHO", "GA", "PSO", "ACO"])
def test_corrective_tsp_exact_budget_feasibility_and_monotone_best(method):
    _, matrix = routing.fixed_tsp(8)
    result = routing.repaired_search(method, matrix, 7, budget=123, pop_size=30)
    trace = result["trace"]
    assert trace.calls == 123
    assert trace.invalid_calls == 0
    assert result["validation"]["valid"]
    assert np.isclose(result["returned_objective"], routing.tour_cost(result["route"], matrix))
    assert all(b <= a for a, b in zip([h["best_feasible"] for h in trace.history],
                                    [h["best_feasible"] for h in trace.history][1:]))


@pytest.mark.parametrize("method", ["EHO", "PSO"])
def test_corrective_vrp_has_feasible_return_at_exact_budget(method):
    _, matrix, demands, cap, fleet = routing.fixed_vrp()
    result = routing.repaired_search(method, matrix, 11, budget=123,
                                    vrp=(demands, cap, fleet))
    assert result["trace"].calls == 123
    assert result["validation"]["valid"]
    assert np.isclose(result["returned_objective"], routing.vrp_distance(result["route"], matrix))


def test_unknown_method_rejected_before_loop():
    _, matrix = routing.fixed_tsp(8)
    with pytest.raises(ValueError, match="Unknown routing method"):
        routing.repaired_search("unknown", matrix, 0)


def test_historical_singleton_clans_do_no_follower_update():
    _, matrix = routing.fixed_tsp(8)
    result = routing.faithful_tsp("EHO", matrix, 0)
    assert result["config"]["population"] == result["config"]["herds"] == 100
    assert result["trace"].calls == 100
    assert result["crossover_calls"] == result["mutation_calls"] == 0
    assert result["validation"]["valid"]


def test_legacy_vrp_objective_rewards_missing_customers_without_penalty():
    records = routing.defect_demonstrations()
    valid, missing, duplicate, depot_only = records
    assert valid["validation"]["valid"]
    assert not missing["validation"]["valid"]
    assert missing["legacy_distance_score"] < valid["legacy_distance_score"]
    assert not duplicate["validation"]["valid"]
    assert not depot_only["validation"]["valid"]
    assert depot_only["legacy_distance_score"] == 0


def test_snippets_recover_two_original_programs_and_no_mri_functions():
    raw, blocks, starts = replay_snippets.recover_blocks(replay_snippets.DEFAULT_SOURCE)
    assert len(blocks) == 2
    assert "num_cities = 15" in blocks[0]
    assert "num_cities = 95" in blocks[1]
    assert "run_comparison_for_95_cities()" in blocks[1]
    assert "".join(blocks).encode() == raw
    assert starts[0] == 1 and starts[1] > 1
