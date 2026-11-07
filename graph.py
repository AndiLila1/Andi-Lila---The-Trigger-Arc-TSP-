"""Data structures for directed Trigger Arc TSP instances."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Arc:
    index: int
    tail: int
    head: int
    cost: int


@dataclass(frozen=True, slots=True)
class Relationship:
    index: int
    trigger_arc: int
    target_arc: int
    new_cost: int


@dataclass(slots=True)
class Graph:
    node_count: int
    arcs: tuple[Arc, ...]
    relationships: tuple[Relationship, ...]
    _arc_by_index: dict[int, Arc] = field(init=False, repr=False)
    _arc_by_endpoints: dict[tuple[int, int], Arc] = field(init=False, repr=False)
    _arcs_by_endpoints: dict[tuple[int, int], tuple[Arc, ...]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.node_count < 1:
            raise ValueError("A graph must contain at least one node")
        if len({a.index for a in self.arcs}) != len(self.arcs):
            raise ValueError("Arc indices must be unique")
        if len({r.index for r in self.relationships}) != len(self.relationships):
            raise ValueError("Relationship indices must be unique")
        self._arc_by_index = {a.index: a for a in self.arcs}
        endpoint_groups: dict[tuple[int, int], list[Arc]] = {}
        for arc in self.arcs:
            endpoint_groups.setdefault((arc.tail, arc.head), []).append(arc)
        self._arcs_by_endpoints = {key: tuple(value) for key, value in endpoint_groups.items()}
        self._arc_by_endpoints = {key: value[0] for key, value in self._arcs_by_endpoints.items()}
        for arc in self.arcs:
            if not (0 <= arc.tail < self.node_count and 0 <= arc.head < self.node_count):
                raise ValueError(f"Arc {arc.index} references a node outside the graph")
        for rel in self.relationships:
            if rel.trigger_arc not in self._arc_by_index:
                raise ValueError(f"Relationship {rel.index} references missing trigger arc {rel.trigger_arc}")
            if rel.target_arc not in self._arc_by_index:
                raise ValueError(f"Relationship {rel.index} references missing target arc {rel.target_arc}")

    def arc(self, index: int) -> Arc:
        return self._arc_by_index[index]

    def arc_between(self, tail: int, head: int) -> Arc | None:
        return self._arc_by_endpoints.get((tail, head))

    def arcs_between(self, tail: int, head: int) -> tuple[Arc, ...]:
        """Return all directed arcs between two nodes, including parallel arcs."""
        return self._arcs_by_endpoints.get((tail, head), ())

    @property
    def outgoing(self) -> tuple[tuple[Arc, ...], ...]:
        result: list[list[Arc]] = [[] for _ in range(self.node_count)]
        for arc in self.arcs:
            result[arc.tail].append(arc)
        return tuple(tuple(row) for row in result)
