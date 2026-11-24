

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from graph import Graph
from solution import CycleEvaluator, Solution


@dataclass(frozen=True, slots=True)
class SearchConfig:
    iterations: int = 100_000
    seconds: float | None = None
    seed: int | None = None
    initial_temperature: float = 100.0
    cooling: float = 0.99995
    restarts: int = 20


@dataclass(frozen=True, slots=True)
class GraspConfig:
    """Settings for GRASP construction and local improvement."""

    iterations: int = 50
    seconds: float | None = None
    seed: int | None = None
    alpha: float = 0.25
    stagnation_limit: int = 100


def _random_cycle(
    graph: Graph,
    rng: random.Random,
    deadline: float | None = None,
    outgoing_neighbors: tuple[tuple[int, ...], ...] | None = None,
) -> tuple[int, ...] | None:
    n = graph.node_count
    if n == 1:
        return (0,) if graph.arc_between(0, 0) else None
    if outgoing_neighbors is None:
        outgoing_neighbors = tuple(
            tuple(dict.fromkeys(arc.head for arc in row)) for row in graph.outgoing
        )
    path = [0]
    used = {0}

    def visit(node: int) -> bool:
        if deadline is not None and time.monotonic() >= deadline:
            return False
        if len(path) == n:
            return graph.arc_between(node, 0) is not None
        choices = [head for head in outgoing_neighbors[node] if head not in used]
        rng.shuffle(choices)
        for nxt in choices:
            path.append(nxt)
            used.add(nxt)
            if visit(nxt):
                return True
            used.remove(nxt)
            path.pop()
        return False

    return tuple(path) if visit(0) else None


def _move(route: tuple[int, ...], rng: random.Random) -> tuple[int, ...]:
    """Return a neighboring permutation while keeping the depot fixed at index 0."""
    n = len(route)
    if n < 3:
        return route

    move = rng.randrange(3)
    left = rng.randrange(1, n)
    right = rng.randrange(1, n - 1)
    if right >= left:
        right += 1

    if move == 0:
        if left > right:
            left, right = right, left
        return route[:left] + tuple(reversed(route[left:right + 1])) + route[right + 1:]
    if move == 1:
        changed = list(route)
        changed[left], changed[right] = changed[right], changed[left]
        return tuple(changed)

    changed = list(route)
    node = changed.pop(left)
    changed.insert(right, node)
    return tuple(changed)


def solve(graph: Graph, config: SearchConfig | None = None) -> Solution | None:
    config = config or SearchConfig()
    rng = random.Random(config.seed)
    evaluator = CycleEvaluator(graph)
    best: Solution | None = None
    deadline = time.monotonic() + config.seconds if config.seconds is not None else None
    outgoing_neighbors = tuple(
        tuple(dict.fromkeys(arc.head for arc in row)) for row in graph.outgoing
    )
    for _ in range(max(1, config.restarts)):
        if deadline is not None and time.monotonic() >= deadline:
            break
        route = _random_cycle(graph, rng, deadline, outgoing_neighbors)
        if route is None:
            continue
        cost, arc_ids = evaluator.evaluate_with_arcs(route, known_permutation=True)
        current_route = route
        current_cost = cost
        if best is None or cost < best.cost:
            best = Solution(current_route, current_cost, arc_ids)
        temperature = max(config.initial_temperature, 1e-9)
        for _step in range(max(0, config.iterations)):
            if deadline is not None and time.monotonic() >= deadline:
                break
            candidate_route = _move(current_route, rng)
            candidate_cost = evaluator.evaluate(candidate_route, known_permutation=True)
            delta = candidate_cost - current_cost
            if delta <= 0 or rng.random() < math.exp(-delta / temperature):
                current_route = candidate_route
                current_cost = candidate_cost
                if best is None or current_cost < best.cost:
                    _, best_arc_ids = evaluator.evaluate_with_arcs(
                        current_route, known_permutation=True
                    )
                    best = Solution(current_route, current_cost, best_arc_ids)
            temperature *= config.cooling
            if temperature < 1e-9:
                temperature = max(config.initial_temperature * 0.05, 1e-9)
    return best

def _greedy_random_cycle(
    graph: Graph,
    rng: random.Random,
    alpha: float,
    deadline: float | None = None,
    outgoing_neighbors: tuple[tuple[int, ...], ...] | None = None,
) -> tuple[int, ...] | None:
    """Build a feasible cycle, randomizing among relatively cheap next nodes."""
    n = graph.node_count
    if n == 1:
        return (0,) if graph.arc_between(0, 0) else None
    if outgoing_neighbors is None:
        outgoing_neighbors = tuple(
            tuple(dict.fromkeys(arc.head for arc in row)) for row in graph.outgoing
        )

    route = [0]
    used = {0}

    def visit(node: int) -> bool:
        if deadline is not None and time.monotonic() >= deadline:
            return False
        if len(route) == n:
            return graph.arc_between(node, 0) is not None

        candidates: list[tuple[int | float, int]] = []
        for nxt in outgoing_neighbors[node]:
            if nxt in used:
                continue
            arcs = graph.arcs_between(node, nxt)
            if arcs:
                # Initial costs guide construction; the evaluator later accounts
                # exactly for all trigger changes and parallel-arc choices.
                candidates.append((min(arc.cost for arc in arcs), nxt))
        if not candidates:
            return False

        low = min(cost for cost, _ in candidates)
        high = max(cost for cost, _ in candidates)
        threshold = low + alpha * (high - low)
        restricted = [nxt for cost, nxt in candidates if cost <= threshold]
        rng.shuffle(restricted)
        for nxt in restricted:
            route.append(nxt)
            used.add(nxt)
            if visit(nxt):
                return True
            used.remove(nxt)
            route.pop()
        return False

    return tuple(route) if visit(0) else None


def _grasp_local_search(
    graph: Graph,
    evaluator: CycleEvaluator,
    route: tuple[int, ...],
    rng: random.Random,
    stagnation_limit: int,
    deadline: float | None = None,
) -> tuple[int, ...]:
    """Apply first-improvement 2-opt, swap, and reinsertion moves."""
    current_route = route
    current_cost = evaluator.evaluate(current_route, known_permutation=True)
    no_improvement = 0
    max_steps = max(stagnation_limit * 25, graph.node_count * graph.node_count * 10)

    for _ in range(max_steps):
        if no_improvement >= stagnation_limit:
            break
        if deadline is not None and time.monotonic() >= deadline:
            break
        candidate = _move(current_route, rng)
        candidate_cost = evaluator.evaluate(candidate, known_permutation=True)
        if candidate_cost < current_cost:
            current_route = candidate
            current_cost = candidate_cost
            no_improvement = 0
        else:
            no_improvement += 1
    return current_route


def solve_grasp(graph: Graph, config: GraspConfig | None = None) -> Solution | None:
    """Solve with Greedy Randomized Adaptive Search Procedure (GRASP)."""
    config = config or GraspConfig()
    if not 0.0 <= config.alpha <= 1.0:
        raise ValueError("GRASP alpha must be between 0 and 1")
    rng = random.Random(config.seed)
    evaluator = CycleEvaluator(graph)
    best: Solution | None = None
    deadline = time.monotonic() + config.seconds if config.seconds is not None else None
    outgoing_neighbors = tuple(
        tuple(dict.fromkeys(arc.head for arc in row)) for row in graph.outgoing
    )

    for _ in range(max(1, config.iterations)):
        if deadline is not None and time.monotonic() >= deadline:
            break
        route = _greedy_random_cycle(
            graph, rng, config.alpha, deadline, outgoing_neighbors
        )
        # The restricted candidate list can dead-end on sparse graphs; fall back
        # to the complete randomized DFS constructor before declaring failure.
        if route is None and (deadline is None or time.monotonic() < deadline):
            route = _random_cycle(graph, rng, deadline, outgoing_neighbors)
        if route is None:
            continue
        improved_route = _grasp_local_search(
            graph,
            evaluator,
            route,
            rng,
            max(1, config.stagnation_limit),
            deadline,
        )
        cost, arc_ids = evaluator.evaluate_with_arcs(
            improved_route, known_permutation=True
        )
        if cost != float("inf") and (best is None or cost < best.cost):
            best = Solution(improved_route, cost, arc_ids)
    return best

