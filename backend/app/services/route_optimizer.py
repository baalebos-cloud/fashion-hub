"""Stop sequencing for one rider: pickups and drop-offs for several orders (pickup-and-delivery
problem with capacity, optional time windows and a maximum route duration).

Pure functions, no database or network. Callers pass a travel-time matrix.

Solvers
  exact_dp   Dynamic programming over (visited stops, current stop). It's optimal and deterministic, and
             used up to EXACT_MAX_STOPS stops (a motorbike batch of 2-4 orders is 4-8 stops).
  insertion  Cheapest feasible insertion, order by order, for larger batches. It's fast and bounded, but
             not guaranteed optimal.

Constraints are hard: if no order of stops satisfies them, the result says infeasible with the
reason, and nothing is silently accepted.

Why not OR-Tools here: a rider's batch is small enough for an exact answer in milliseconds, and
OR-Tools is a large compiled dependency. Fleet-wide planning (many riders at once, CVRP/VRPTW) is
where OR-Tools fits; `Solver` below is the seam for adding it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

EXACT_MAX_STOPS = 12
INSERTION_TIME_BUDGET_S = 0.5
SERVICE_MINUTES = {"pickup": 3, "dropoff": 4}   # handing over takes a few minutes


@dataclass(frozen=True)
class Stop:
    key: str                 # unique, e.g. "<delivery_id>:pickup"
    job: str                 # delivery id: pairs a pickup with its drop-off
    kind: str                # "pickup" | "dropoff"
    point: int               # index into the travel-time matrix
    load: int = 1            # units this order occupies on the vehicle
    earliest: int | None = None   # minutes from start; None = no window
    latest: int | None = None
    done: bool = False       # already visited (e.g. package already collected)


@dataclass
class Plan:
    feasible: bool
    stops: list[dict] = field(default_factory=list)   # ordered, with eta_minutes and load_after
    total_minutes: int | None = None
    solver: str = ""
    reason: str | None = None
    baseline_minutes: int | None = None             # one order after another, for comparison
    solve_ms: int = 0


def _service(stop: Stop) -> int:
    return SERVICE_MINUTES[stop.kind]


def _simulate(order: list[Stop], start: int, matrix, capacity: int, start_load: int, max_minutes: int | None):
    """Walk a stop order. Returns (ok, total_minutes, timeline, reason)."""
    now, here, load, timeline = 0, start, start_load, []
    # A drop-off whose pickup isn't in this route was collected earlier: it's already on board.
    picked = {s.job for s in order if s.kind == "dropoff"} - {s.job for s in order if s.kind == "pickup"}
    for stop in order:
        now += matrix[here][stop.point]
        if stop.earliest is not None and now < stop.earliest:
            now = stop.earliest  # wait for the window to open
        if stop.latest is not None and now > stop.latest:
            return False, None, None, f"misses the time window at {stop.key}"
        if stop.kind == "pickup":
            load += stop.load
            picked.add(stop.job)
            if load > capacity:
                return False, None, None, "more packages than the vehicle can carry"
        else:
            if stop.job not in picked:
                return False, None, None, "drop-off before pickup"
            load -= stop.load
        now += _service(stop)
        timeline.append({"key": stop.key, "job": stop.job, "kind": stop.kind, "eta_minutes": now - _service(stop),
                         "load_after": load})
        here = stop.point
        if max_minutes is not None and now > max_minutes:
            return False, None, None, f"route longer than {max_minutes} minutes"
    return True, now, timeline, None


def _baseline(pending: list[Stop], start, matrix, capacity, start_load, max_minutes):
    """One order at a time: finish packages already on board, then each new pickup then its drop-off."""
    pickups = {s.job for s in pending if s.kind == "pickup"}
    order = sorted((s for s in pending if s.kind == "dropoff" and s.job not in pickups), key=lambda s: s.key)
    for job in sorted(pickups):
        order += [s for s in pending if s.job == job and s.kind == "pickup"] + \
                 [s for s in pending if s.job == job and s.kind == "dropoff"]
    ok, total, _, _ = _simulate(order, start, matrix, 10 ** 6, start_load, None)
    return total if ok else None


def _step(state, here, stop: Stop, matrix, capacity, max_minutes):
    """Advance (time, load) by visiting `stop` from matrix index `here`; None if a constraint fails."""
    now, load = state
    now += matrix[here][stop.point]
    if stop.earliest is not None and now < stop.earliest:
        now = stop.earliest
    if stop.latest is not None and now > stop.latest:
        return None
    load = load + stop.load if stop.kind == "pickup" else load - stop.load
    if load > capacity:
        return None
    now += _service(stop)
    if max_minutes is not None and now > max_minutes:
        return None
    return now, load


def _exact(pending: list[Stop], start, matrix, capacity, start_load, max_minutes):
    """Dynamic programming over (visited set, last stop), keeping the earliest finish time.
    Waiting is allowed, so arriving earlier is never worse: keeping the minimum time is optimal."""
    n = len(pending)
    pickup_of = {i: next((j for j, t in enumerate(pending) if t.job == s.job and t.kind == "pickup"), None)
                 for i, s in enumerate(pending) if s.kind == "dropoff"}
    best: dict[tuple[int, int], tuple[int, int, tuple]] = {}
    for i, stop in enumerate(pending):
        if stop.kind == "dropoff" and pickup_of[i] is not None:
            continue
        state = _step((0, start_load), start, stop, matrix, capacity, max_minutes)
        if state:
            best[(1 << i, i)] = (state[0], state[1], (i,))
    for mask in range(1, 1 << n):
        for last in range(n):
            entry = best.get((mask, last))
            if entry is None:
                continue
            now, load, path = entry
            for j in range(n):
                if mask & (1 << j):
                    continue
                if pending[j].kind == "dropoff" and pickup_of[j] is not None and not mask & (1 << pickup_of[j]):
                    continue
                state = _step((now, load), pending[last].point, pending[j], matrix, capacity, max_minutes)
                if state is None:
                    continue
                key = (mask | (1 << j), j)
                candidate = (state[0], state[1], path + (j,))
                if key not in best or (candidate[0], candidate[2]) < (best[key][0], best[key][2]):
                    best[key] = candidate
    full = (1 << n) - 1
    finals = [best[(full, last)] for last in range(n) if (full, last) in best]
    if not finals:
        return None
    _, _, path = min(finals, key=lambda c: (c[0], c[2]))
    return [pending[k] for k in path]


def _insertion(pending: list[Stop], start, matrix, capacity, start_load, max_minutes):
    deadline = time.monotonic() + INSERTION_TIME_BUDGET_S
    route = [s for s in pending if s.kind == "dropoff" and not any(p.job == s.job and p.kind == "pickup" for p in pending)]
    route.sort(key=lambda s: s.key)
    for job in sorted({s.job for s in pending if s.kind == "pickup"}):
        pickup = next(s for s in pending if s.job == job and s.kind == "pickup")
        dropoff = next(s for s in pending if s.job == job and s.kind == "dropoff")
        choice = None
        for i in range(len(route) + 1):
            for j in range(i + 1, len(route) + 2):
                if time.monotonic() > deadline:
                    break
                trial = route[:i] + [pickup] + route[i:]
                trial = trial[:j] + [dropoff] + trial[j:]
                ok, total, _, _ = _simulate(trial, start, matrix, capacity, start_load, max_minutes)
                if ok and (choice is None or total < choice[0]):
                    choice = (total, trial)
        if choice is None:
            return None
        route = choice[1]
    return route


def plan_route(stops: list[Stop], *, start: int, matrix, capacity: int, max_minutes: int | None = None) -> Plan:
    """Best order for the remaining stops, starting from matrix index `start`."""
    began = time.monotonic()
    pending = [s for s in stops if not s.done]
    start_load = sum(s.load for s in stops if s.kind == "pickup" and s.done
                     and any(d.job == s.job and d.kind == "dropoff" and not d.done for d in stops))
    if start_load > capacity:
        return Plan(feasible=False, reason="more packages on board than the vehicle can carry", solver="none")
    if not pending:
        return Plan(feasible=True, stops=[], total_minutes=0, solver="none")
    exact = len(pending) <= EXACT_MAX_STOPS
    order = (_exact if exact else _insertion)(pending, start, matrix, capacity, start_load, max_minutes)
    elapsed = round((time.monotonic() - began) * 1000)
    if order is None:
        # Say why: does it work with unlimited capacity? Then capacity is the problem.
        solve = _exact if exact else _insertion
        if solve(pending, start, matrix, 10 ** 6, start_load, max_minutes) is not None:
            reason = "more packages than the vehicle can carry at once"
        else:
            reason = "no order of stops meets the time limit or delivery windows"
        return Plan(feasible=False, solver="exact_dp" if exact else "insertion", reason=reason, solve_ms=elapsed)
    ok, total, timeline, why = _simulate(order, start, matrix, capacity, start_load, max_minutes)
    if not ok:  # defensive: never report a plan we can't replay
        return Plan(feasible=False, solver="exact_dp" if exact else "insertion", reason=why, solve_ms=elapsed)
    return Plan(feasible=True, stops=timeline, total_minutes=total, solver="exact_dp" if exact else "insertion",
                baseline_minutes=_baseline(pending, start, matrix, capacity, start_load, max_minutes), solve_ms=elapsed)
