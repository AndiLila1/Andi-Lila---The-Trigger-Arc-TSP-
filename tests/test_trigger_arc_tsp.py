import unittest

from brute_force import brute_force
from graph import Arc, Graph, Relationship
from metaheuristic import SearchConfig, solve
from parser import parse_instance_text
from solution import evaluate_cycle, validate_cycle


class TriggerArcTests(unittest.TestCase):
    def test_parse_instance_and_endpoint_consistency(self):
        graph = parse_instance_text("""3 3 1
0 0 1 4
1 1 2 5
2 2 0 6
0 0 0 1 1 1 2 2
""")
        self.assertEqual(graph.node_count, 3)
        self.assertEqual(evaluate_cycle(graph, (0, 1, 2)), 12)
        with self.assertRaises(ValueError):
            parse_instance_text("""3 3 1
0 0 1 4
1 1 2 5
2 2 0 6
0 0 0 2 1 1 2 2
""")

    def test_trigger_changes_unvisited_target(self):
        graph = Graph(3, (Arc(0, 0, 1, 1), Arc(1, 1, 2, 10), Arc(2, 2, 0, 1)),
                      (Relationship(0, 0, 1, 3),))
        self.assertEqual(evaluate_cycle(graph, (0, 1, 2)), 5)

    def test_last_trigger_for_same_target_wins(self):
        graph = Graph(4, (Arc(0, 0, 1, 1), Arc(1, 1, 2, 1), Arc(2, 2, 3, 10), Arc(3, 3, 0, 1)),
                      (Relationship(0, 0, 2, 4), Relationship(1, 1, 2, 2)))
        self.assertEqual(evaluate_cycle(graph, (0, 1, 2, 3)), 5)

    def test_trigger_after_target_does_not_change_visited_arc(self):
        graph = Graph(3, (Arc(0, 0, 1, 1), Arc(1, 1, 2, 10), Arc(2, 2, 0, 1)),
                      (Relationship(0, 2, 1, 2),))
        self.assertEqual(evaluate_cycle(graph, (0, 1, 2)), 12)

    def test_parallel_arc_choice_accounts_for_trigger_effects(self):
        graph = Graph(2, (Arc(0, 0, 1, 10), Arc(1, 0, 1, 2), Arc(2, 1, 0, 20)),
                      (Relationship(0, 0, 2, 1),))
        result = solve(graph, SearchConfig(iterations=0, seed=1, restarts=1))
        self.assertIsNotNone(result)
        self.assertEqual(result.cost, 11)
        self.assertEqual(result.arc_ids, (0, 2))
        exact = brute_force(graph)
        self.assertIsNotNone(exact)
        self.assertEqual((exact.cost, exact.arc_ids), (11, (0, 2)))

    def test_hamiltonian_cycle_validation_and_invalid_cost(self):
        graph = Graph(3, (Arc(0, 0, 1, 1), Arc(1, 1, 2, 1), Arc(2, 2, 0, 1)), ())
        self.assertTrue(validate_cycle(graph, (0, 1, 2)))
        self.assertFalse(validate_cycle(graph, (0, 2, 1)))
        self.assertFalse(validate_cycle(graph, (0, 1, 1)))

    def test_bruteforce_and_search_on_tiny_complete_instance(self):
        arcs = []
        index = 0
        for u in range(4):
            for v in range(4):
                if u != v:
                    arcs.append(Arc(index, u, v, (u * 3 + v * 2) % 9 + 1))
                    index += 1
        graph = Graph(4, tuple(arcs), (Relationship(0, 0, 7, 1), Relationship(1, 5, 2, 12)))
        exact = brute_force(graph)
        result = solve(graph, SearchConfig(iterations=500, seed=7, restarts=3))
        self.assertIsNotNone(exact)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.cost, exact.cost)
        self.assertTrue(validate_cycle(graph, result.nodes))


if __name__ == "__main__":
    unittest.main()
