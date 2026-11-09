"""Simulated annealing with trigger-aware 2-opt, swap, and reinsertion moves."""

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


def _random_cycle(
    graph: Graph, rng: random.Random, deadline: float | None = None
) -> tuple[int, ...] | None:
    n = graph.node_count
    if n == 1:
        return (0,) if graph.arc_between(0, 0) else None
    outgoing = graph.outgoing
    # Randomized backtracking searches until a cycle is found or the run deadline expires.
    # A fixed attempt budget could incorrectly report that no tour exists in a sparse graph.
    path = [0]
    used = {0}

    def visit(node: int) -> bool:
        if deadline is not None and time.monotonic() >= deadline:
            return False
        if len(path) == n:
            return graph.arc_between(node, 0) is not None
        choices = list(dict.fromkeys(arc.head for arc in outgoing[node] if arc.head not in used))
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
    move = rng.choice(("2opt", "swap", "reinsert"))
    if move == "2opt":
        left, right = sorted(rng.sample(range(1, n), 2))
        return route[:left] + tuple(reversed(route[left:right + 1])) + route[right + 1:]
    if move == "swap":
        left, right = rng.sample(range(1, n), 2)
        changed = list(route)
        changed[left], changed[right] = changed[right], changed[left]
        return tuple(changed)

    source, destination = rng.sample(range(1, n), 2)
    changed = list(route)
    node = changed.pop(source)
    changed.insert(destination, node)
    return tuple(changed)


def solve(graph: Graph, config: SearchConfig | None = None) -> Solution | None:
    config = config or SearchConfig()
    rng = random.Random(config.seed)
    evaluator = CycleEvaluator(graph)
    best: Solution | None = None
    deadline = time.monotonic() + config.seconds if config.seconds is not None else None
    for _ in range(max(1, config.restarts)):
        if deadline is not None and time.monotonic() >= deadline:
            break
        route = _random_cycle(graph, rng, deadline)
        if route is None:
            continue
        cost, arc_ids = evaluator.evaluate_with_arcs(route, known_permutation=True)
        current = Solution(route, cost, arc_ids)
        if best is None or cost < best.cost:
            best = current
        temperature = max(config.initial_temperature, 1e-9)
        for _step in range(max(0, config.iterations)):
            if deadline is not None and time.monotonic() >= deadline:
                break
            candidate_route = _move(current.nodes, rng)
            candidate_cost, candidate_arcs = evaluator.evaluate_with_arcs(
                candidate_route, known_permutation=True
            )
            delta = candidate_cost - current.cost
            if delta <= 0 or rng.random() < math.exp(-delta / temperature):
                current = Solution(candidate_route, candidate_cost, candidate_arcs)
                if best is None or current.cost < best.cost:
                    best = current
            temperature *= config.cooling
            if temperature < 1e-9:
                temperature = max(config.initial_temperature * 0.05, 1e-9)
    return best
