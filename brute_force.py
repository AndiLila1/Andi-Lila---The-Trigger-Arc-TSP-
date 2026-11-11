"""Exact enumerator for small instances, intended for verification."""

from __future__ import annotations

from itertools import permutations
from graph import Graph
from solution import CycleEvaluator, Solution


def brute_force(graph: Graph) -> Solution | None:
    evaluator = CycleEvaluator(graph)
    if graph.node_count == 1:
        route = (0,)
        cost, arc_ids = evaluator.evaluate_with_arcs(route, known_permutation=True)
        return Solution(route, cost, arc_ids) if cost != float("inf") else None
    best: Solution | None = None
    for order in permutations(range(1, graph.node_count)):
        route = (0, *order)
        cost = evaluator.evaluate(route, known_permutation=True)
        if cost != float("inf") and (best is None or cost < best.cost):
            best = Solution(route, cost)
    if best is not None:
        cost, arc_ids = evaluator.evaluate_with_arcs(best.nodes, known_permutation=True)
        best = Solution(best.nodes, cost, arc_ids)
    return best
