"""Strict parser for the UTF-8 instance format described in MESS2024Catania."""

from __future__ import annotations

from pathlib import Path
from graph import Arc, Graph, Relationship


def parse_instance_text(text: str) -> Graph:
    lines = [(number, line.split()) for number, line in enumerate(text.splitlines(), 1) if line.strip()]
    if not lines:
        raise ValueError("Instance is empty")

    def take(pos: int, width: int, kind: str) -> tuple[list[str], int]:
        if pos >= len(lines):
            raise ValueError(f"Missing {kind} record")
        line_no, fields = lines[pos]
        if len(fields) != width:
            raise ValueError(f"Line {line_no}: expected {width} fields for {kind}, got {len(fields)}")
        try:
            values = [int(field) for field in fields]
        except ValueError as exc:
            raise ValueError(f"Line {line_no}: {kind} fields must be integers") from exc
        return values, pos + 1

    header, pos = take(0, 3, "header")
    node_count, arc_count, relationship_count = header
    if node_count <= 0 or arc_count < 0 or relationship_count < 0:
        raise ValueError("Header counts must be nonnegative and node count must be positive")
    arcs: list[Arc] = []
    for _ in range(arc_count):
        values, pos = take(pos, 4, "arc")
        arcs.append(Arc(*values))
    relationships: list[Relationship] = []
    relationship_endpoints: list[tuple[int, int, int, int]] = []
    for _ in range(relationship_count):
        values, pos = take(pos, 8, "relationship")
        rid, trigger_id, trigger_tail, trigger_head, target_id, target_tail, target_head, new_cost = values
        relationships.append(Relationship(rid, trigger_id, target_id, new_cost))
        relationship_endpoints.append((trigger_tail, trigger_head, target_tail, target_head))
    if pos != len(lines):
        line_no, _ = lines[pos]
        raise ValueError(f"Line {line_no}: unexpected extra record")
    graph = Graph(node_count, tuple(arcs), tuple(relationships))
    # Relationship triples in the file must agree with the referenced arc indices.
    for i, rel in enumerate(relationships):
        trigger_tail, trigger_head, target_tail, target_head = relationship_endpoints[i]
        trigger, target = graph.arc(rel.trigger_arc), graph.arc(rel.target_arc)
        if (trigger.tail, trigger.head) != (trigger_tail, trigger_head):
            raise ValueError(f"Relationship {rel.index}: trigger arc endpoints do not match arc {trigger.index}")
        if (target.tail, target.head) != (target_tail, target_head):
            raise ValueError(f"Relationship {rel.index}: target arc endpoints do not match arc {target.index}")
    return graph


def parse_instance(path: str | Path) -> Graph:
    return parse_instance_text(Path(path).read_text(encoding="utf-8"))
