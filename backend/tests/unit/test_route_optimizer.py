"""Multi-stop planner: correctness against brute force, and the hard constraints."""
import itertools
import random

import pytest

from app.services.route_optimizer import SERVICE_MINUTES, Stop, plan_route, _simulate


def _orders(n_orders, collected=()):
    stops = []
    for k in range(n_orders):
        stops.append(Stop(f"j{k}:pickup", f"j{k}", "pickup", 1 + 2 * k, done=k in collected))
        stops.append(Stop(f"j{k}:dropoff", f"j{k}", "dropoff", 2 + 2 * k))
    return stops


def _matrix(n, seed):
    rng = random.Random(seed)
    return [[0 if i == j else rng.randint(2, 30) for j in range(n)] for i in range(n)]


def _brute_force(stops, matrix, capacity):
    pending = [s for s in stops if not s.done]
    start_load = sum(1 for s in stops if s.done)
    best = None
    for order in itertools.permutations(pending):
        ok, total, _, _ = _simulate(list(order), 0, matrix, capacity, start_load, None)
        if ok and (best is None or total < best):
            best = total
    return best


@pytest.mark.parametrize("seed", range(12))
def test_exact_solver_matches_brute_force_and_respects_constraints(seed):
    stops = _orders(3, collected={0} if seed % 3 == 0 else ())
    matrix = _matrix(7, seed)
    capacity = 2 if seed % 2 else 3
    plan = plan_route(stops, start=0, matrix=matrix, capacity=capacity)
    expected = _brute_force(stops, matrix, capacity)
    assert plan.feasible == (expected is not None)
    if plan.feasible:
        assert plan.total_minutes == expected and plan.solver == "exact_dp"
        seen = {s.job for s in stops if s.done}
        for stop in plan.stops:
            if stop["kind"] == "pickup":
                seen.add(stop["job"])
            else:
                assert stop["job"] in seen  # every pickup precedes its drop-off
            assert stop["load_after"] <= capacity  # capacity never exceeded


def test_same_input_same_plan():
    stops, matrix = _orders(4), _matrix(9, 42)
    first = plan_route(stops, start=0, matrix=matrix, capacity=3)
    assert [s["key"] for s in first.stops] == [s["key"] for s in plan_route(stops, start=0, matrix=matrix, capacity=3).stops]


def test_infeasible_routes_are_refused_with_a_reason():
    stops = _orders(2)
    matrix = _matrix(5, 1)
    too_long = plan_route(stops, start=0, matrix=matrix, capacity=3, max_minutes=5)
    assert not too_long.feasible and "time limit" in too_long.reason
    on_board = plan_route(_orders(3, collected={0, 1}), start=0, matrix=_matrix(7, 2), capacity=1)
    assert not on_board.feasible and "carry" in on_board.reason


def test_time_windows_make_the_rider_wait_rather_than_arrive_early():
    stops = [Stop("a:pickup", "a", "pickup", 1, earliest=40), Stop("a:dropoff", "a", "dropoff", 2)]
    matrix = [[0, 5, 10], [5, 0, 5], [10, 5, 0]]
    plan = plan_route(stops, start=0, matrix=matrix, capacity=1)
    assert plan.stops[0]["eta_minutes"] == 40
    assert plan.total_minutes == 40 + SERVICE_MINUTES["pickup"] + 5 + SERVICE_MINUTES["dropoff"]
    late = [Stop("a:pickup", "a", "pickup", 1), Stop("a:dropoff", "a", "dropoff", 2, latest=3)]
    assert not plan_route(late, start=0, matrix=matrix, capacity=1).feasible


def test_large_batches_use_bounded_insertion_and_stay_valid():
    stops, matrix = _orders(8), _matrix(17, 7)
    plan = plan_route(stops, start=0, matrix=matrix, capacity=20)
    assert plan.feasible and plan.solver == "insertion" and len(plan.stops) == 16 and plan.solve_ms < 2000
    seen = set()
    for stop in plan.stops:
        if stop["kind"] == "pickup":
            seen.add(stop["job"])
        else:
            assert stop["job"] in seen


def test_optimised_route_is_never_worse_than_one_order_at_a_time():
    for seed in range(8):
        plan = plan_route(_orders(3), start=0, matrix=_matrix(7, seed), capacity=3)
        assert plan.total_minutes <= plan.baseline_minutes
