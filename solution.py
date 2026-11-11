"""Route validation and exact Trigger Arc TSP objective evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from graph import Graph


@dataclass(frozen=True, slots=True)
class Solution:
    nodes: tuple[int, ...]
    cost: int
    arc_ids: tuple[int, ...] = ()


def validate_cycle(graph: Graph, nodes: tuple[int, ...] | list[int]) -> bool:
    if len(nodes) != graph.node_count or not nodes or nodes[0] != 0:
        return False
    if set(nodes) != set(range(graph.node_count)):
        return False
    return all(graph.arc_between(nodes[i], nodes[(i + 1) % len(nodes)]) is not None for i in range(len(nodes)))


class CycleEvaluator:
    """Precompiled evaluator reused across the many candidate tours in a search."""

    __slots__ = ("node_count", "_arcs_by_endpoints", "_by_trigger")

    def __init__(self, graph: Graph) -> None:
        self.node_count = graph.node_count
        self._arcs_by_endpoints = graph._arcs_by_endpoints
        trigger_lists: dict[int, list[tuple[int, int]]] = {}
        for relation in graph.relationships:
            trigger_lists.setdefault(relation.trigger_arc, []).append(
                (relation.target_arc, relation.new_cost)
            )
        self._by_trigger = {key: tuple(value) for key, value in trigger_lists.items()}

    def evaluate(self, nodes: tuple[int, ...] | list[int], *, known_permutation: bool = False) -> int:
        """Return infinity for invalid cycles; otherwise score in traversal order.

        ``known_permutation`` is reserved for search moves, which preserve the node
        permutation and depot position by construction, and avoids rescanning it.
        """
        n = self.node_count
        if not nodes or len(nodes) != n or nodes[0] != 0:
            return inf  # type: ignore[return-value]
        if not known_permutation and set(nodes) != set(range(n)):
            return inf  # type: ignore[return-value]
        options = [
            self._arcs_by_endpoints.get((tail, nodes[(i + 1) % n]), ())
            for i, tail in enumerate(nodes)
        ]
        if any(not arcs for arcs in options):
            return inf  # type: ignore[return-value]

        # Keep the common single-arc case linear and allocation-light.
        if all(len(arcs) == 1 for arcs in options):
            changed_cost: dict[int, int] = {}
            traversed: set[int] = set()
            total = 0
            for arcs in options:
                arc = arcs[0]
                total += changed_cost.get(arc.index, arc.cost)
                traversed.add(arc.index)
                for target, new_cost in self._by_trigger.get(arc.index, ()):
                    if target not in traversed:
                        changed_cost[target] = new_cost
            return total

        # Parallel arc choices can trigger different future costs. Enumerate the
        # choices exactly for this node cycle and keep its cheapest arc sequence.
        changed_cost: dict[int, int] = {}
        traversed: set[int] = set()
        best = inf

        def visit(position: int, total: int) -> None:
            nonlocal best
            if position == n:
                if total < best:
                    best = total
                return
            for arc in options[position]:
                next_total = total + changed_cost.get(arc.index, arc.cost)
                traversed.add(arc.index)
                undo: list[tuple[int, bool, int]] = []
                for target, new_cost in self._by_trigger.get(arc.index, ()):
                    if target not in traversed:
                        had_old = target in changed_cost
                        undo.append((target, had_old, changed_cost.get(target, 0)))
                        changed_cost[target] = new_cost
                visit(position + 1, next_total)
                for target, had_old, old_cost in reversed(undo):
                    if had_old:
                        changed_cost[target] = old_cost
                    else:
                        changed_cost.pop(target, None)
                traversed.remove(arc.index)

        visit(0, 0)
        return best  # type: ignore[return-value]

    def evaluate_with_arcs(
        self, nodes: tuple[int, ...] | list[int], *, known_permutation: bool = False
    ) -> tuple[int, tuple[int, ...]]:
        """Return the minimum cost and selected arc IDs for a Hamiltonian node cycle."""
        if not nodes or len(nodes) != self.node_count or nodes[0] != 0:
            return inf, ()  # type: ignore[return-value]
        if not known_permutation and set(nodes) != set(range(self.node_count)):
            return inf, ()  # type: ignore[return-value]

        options = [
            self._arcs_by_endpoints.get((tail, nodes[(i + 1) % self.node_count]), ())
            for i, tail in enumerate(nodes)
        ]
        if any(not arcs for arcs in options):
            return inf, ()  # type: ignore[return-value]
        if all(len(arcs) == 1 for arcs in options):
            selected = tuple(arcs[0].index for arcs in options)
            return self.evaluate(nodes, known_permutation=True), selected

        changed_cost: dict[int, int] = {}
        traversed: set[int] = set()
        selected_path: list[int] = []
        best_cost = inf
        best_path: tuple[int, ...] = ()

        def visit(position: int, total: int) -> None:
            nonlocal best_cost, best_path
            if position == self.node_count:
                if total < best_cost:
                    best_cost = total
                    best_path = tuple(selected_path)
                return
            for arc in options[position]:
                next_total = total + changed_cost.get(arc.index, arc.cost)
                traversed.add(arc.index)
                selected_path.append(arc.index)
                undo: list[tuple[int, bool, int]] = []
                for target, new_cost in self._by_trigger.get(arc.index, ()):
                    if target not in traversed:
                        had_old = target in changed_cost
                        undo.append((target, had_old, changed_cost.get(target, 0)))
                        changed_cost[target] = new_cost
                visit(position + 1, next_total)
                for target, had_old, old_cost in reversed(undo):
                    if had_old:
                        changed_cost[target] = old_cost
                    else:
                        changed_cost.pop(target, None)
                selected_path.pop()
                traversed.remove(arc.index)

        visit(0, 0)
        return best_cost, best_path  # type: ignore[return-value]


def evaluate_cycle(graph: Graph, nodes: tuple[int, ...] | list[int]) -> int:
    """Evaluate a cycle in traversal order; only the most recent prior trigger applies."""
    return CycleEvaluator(graph).evaluate(nodes)


def make_solution(graph: Graph, nodes: tuple[int, ...] | list[int]) -> Solution:
    if not validate_cycle(graph, nodes):
        raise ValueError("Nodes do not form a directed Hamiltonian cycle from depot 0")
    route = tuple(nodes)
    evaluator = CycleEvaluator(graph)
    cost, arc_ids = evaluator.evaluate_with_arcs(route, known_permutation=True)
    return Solution(route, cost, arc_ids)
