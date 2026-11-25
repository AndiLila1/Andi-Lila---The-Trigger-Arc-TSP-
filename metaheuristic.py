

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

    iterations: int = 100
    seconds: float | None = None
    seed: int | None = None
    alpha: float = 0.25


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
    """Construct a randomized greedy cycle using active trigger costs."""
    n = graph.node_count
    if n == 1:
        return (0,) if graph.arc_between(0, 0) else None
    if outgoing_neighbors is None:
        outgoing_neighbors = tuple(
            tuple(dict.fromkeys(arc.head for arc in row)) for row in graph.outgoing
        )

    by_trigger: dict[int, list[tuple[int, int | float]]] = {}
    for relation in graph.relationships:
        by_trigger.setdefault(relation.trigger_arc, []).append(
            (relation.target_arc, relation.new_cost)
        )

    route = [0]
    used_nodes = {0}

    def visit(
        node: int,
        traversed_arcs: frozenset[int],
        active_costs: dict[int, int | float],
    ) -> bool:
        if deadline is not None and time.monotonic() >= deadline:
            return False
        if len(route) == n:
            return bool(graph.arcs_between(node, 0))

        candidates: list[tuple[int | float, int, int]] = []
        for nxt in outgoing_neighbors[node]:
            if nxt in used_nodes:
                continue
            for arc in graph.arcs_between(node, nxt):
                if arc.index not in traversed_arcs:
                    candidates.append(
                        (active_costs.get(arc.index, arc.cost), arc.index, nxt)
                    )
        if not candidates:
            return False

        low = min(cost for cost, _, _ in candidates)
        high = max(cost for cost, _, _ in candidates)
        threshold = low + alpha * (high - low)
        restricted = [item for item in candidates if item[0] <= threshold]
        rng.shuffle(restricted)

        for _, arc_id, nxt in restricted:
            next_traversed = traversed_arcs | {arc_id}
            next_costs = active_costs.copy()
            # The chosen arc is considered traversed before its triggers fire.
            for target_arc, new_cost in by_trigger.get(arc_id, ()):
                if target_arc not in next_traversed:
                    next_costs[target_arc] = new_cost
            route.append(nxt)
            used_nodes.add(nxt)
            if visit(nxt, next_traversed, next_costs):
                return True
            used_nodes.remove(nxt)
            route.pop()
        return False

    return tuple(route) if visit(0, frozenset(), {}) else None


def _grasp_neighborhood(
    route: tuple[int, ...], neighborhood: int, rng: random.Random
) -> list[tuple[int, ...]]:
    """Enumerate one neighborhood: 2-opt, swap, or relocate."""
    n = len(route)
    candidates: list[tuple[int, ...]] = []
    if neighborhood == 0:
        for left in range(1, n - 1):
            for right in range(left + 1, n):
                candidates.append(
                    route[:left]
                    + tuple(reversed(route[left:right + 1]))
                    + route[right + 1:]
                )
    elif neighborhood == 1:
        for left in range(1, n - 1):
            for right in range(left + 1, n):
                changed = list(route)
                changed[left], changed[right] = changed[right], changed[left]
                candidates.append(tuple(changed))
    else:
        for source in range(1, n):
            for destination in range(1, n):
                # These insertion points reproduce the original order.
                if destination == source:
                    continue
                changed = list(route)
                node = changed.pop(source)
                changed.insert(destination, node)
                candidates.append(tuple(changed))
    rng.shuffle(candidates)
    return candidates


def _grasp_local_search(
    evaluator: CycleEvaluator,
    route: tuple[int, ...],
    rng: random.Random,
    deadline: float | None = None,
    evaluation_limit: int | None = None,
) -> tuple[int, ...]:
    """Run variable-neighborhood descent with exact trigger-aware costs."""
    current_route = route
    current_cost = evaluator.evaluate(current_route, known_permutation=True)
    evaluation_limit = evaluation_limit or max(500, 20 * len(route) * len(route))
    evaluations = 0
    neighborhood = 0

    while neighborhood < 3 and evaluations < evaluation_limit:
        if deadline is not None and time.monotonic() >= deadline:
            break
        improved = False
        for candidate in _grasp_neighborhood(current_route, neighborhood, rng):
            if evaluations >= evaluation_limit:
                break
            if deadline is not None and time.monotonic() >= deadline:
                break
            candidate_cost = evaluator.evaluate(candidate, known_permutation=True)
            evaluations += 1
            if candidate_cost < current_cost:
                current_route = candidate
                current_cost = candidate_cost
                neighborhood = 0
                improved = True
                break
        if not improved:
            neighborhood += 1
    return current_route


def solve_grasp(graph: Graph, config: GraspConfig | None = None) -> Solution | None:
    """Solve with GRASP: trigger-aware randomized construction plus VND."""
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
        # If the restricted candidate list dead-ends, try the complete randomized
        # constructor so a feasible cycle is not missed on a sparse graph.
        if route is None and (deadline is None or time.monotonic() < deadline):
            route = _random_cycle(graph, rng, deadline, outgoing_neighbors)
        if route is None:
            continue
        improved_route = _grasp_local_search(evaluator, route, rng, deadline)
        cost, arc_ids = evaluator.evaluate_with_arcs(
            improved_route, known_permutation=True
        )
        if math.isfinite(cost) and (best is None or cost < best.cost):
            best = Solution(improved_route, cost, arc_ids)
    return best

