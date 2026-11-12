

from __future__ import annotations

import argparse
from pathlib import Path
from metaheuristic import SearchConfig, solve
from parser import parse_instance


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve a MESS2024 Trigger Arc TSP instance")
    parser.add_argument("instance", help="UTF-8 instance text file")
    parser.add_argument("--iterations", type=int, default=100_000)
    parser.add_argument("--seconds", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--restarts", type=int, default=20)
    args = parser.parse_args()
    instance_path = Path(args.instance)
    if not instance_path.is_file():
        parser.error(
            f"instance file not found: {instance_path}\n"
            "Replace the example path with the real path to a downloaded .txt instance, "
            "for example: python main.py .\\examples\\small_instance.txt --seconds 30 --seed 42"
        )
    try:
        graph = parse_instance(instance_path)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(f"could not read instance '{instance_path}': {exc}")
    solution = solve(graph, SearchConfig(args.iterations, args.seconds, args.seed, restarts=args.restarts))
    if solution is None:
        print("No feasible Hamiltonian cycle found within the configured search limits.")
        return 2
    print(f"cost: {solution.cost}")
    print("node_cycle: " + " ".join(map(str, (*solution.nodes, 0))))
    print("arc_ids: " + " ".join(map(str, solution.arc_ids)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
