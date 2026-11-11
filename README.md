# Trigger Arc TSP (MESS 2024)

Python implementation of the directed Trigger Arc TSP described in `MESS2024Catania .pdf`.
It reads the documented UTF-8 instance format, validates directed Hamiltonian cycles,
evaluates trigger-dependent arc costs in traversal order, runs simulated annealing with
2-opt, swap, and reinsertion moves, and includes an exact enumerator for small-instance
checks. This is a local solver; it does not upload results to the competition portal.

## Requirements and run (Windows)

Python 3.10 or newer is recommended. The implementation uses only the standard library;
there are no packages to install. From PowerShell in this directory:

```powershell
python main.py path\to\instance.txt --seconds 30 --seed 42
```

You can instead set `--iterations 100000 --restarts 20`. The default search limit is
100,000 iterations for each of 20 restarts. `--seconds` adds a wall-clock cutoff.

Run the correctness checks with:

```powershell
python -m unittest discover -s tests -v
```

## Instance format

The parser follows the PDF: `|N| |A| |R|`; then one row per arc `arc_id tail head cost`;
then one row per relation `relation_id trigger_id trigger_tail trigger_head target_id
target_tail target_head new_target_cost`. Relationship endpoint pairs are checked against
the referenced arc IDs. Node 0 is the depot. Arcs are directed and must have unique IDs.
Parallel arcs are supported; for each node-to-node step, the evaluator selects the arc ID
that gives the lowest trigger-aware cost for that complete cycle.

## Cost semantics

An arc is charged at its current cost when traversed. Immediately afterward, its outgoing
trigger relations update their target arc costs if those targets have not already been
traversed. If multiple triggers for one target are encountered before the target, the last
encountered trigger supplies the cost. A trigger encountered after a target has been used
has no effect on that tour's cost.

## Search choice and complexity

Simulated annealing with 2-opt reversal, swap, and reinsertion moves was selected because
each candidate route is cheap to generate. The search compiles endpoint and trigger lookups
once, then scores each candidate in O(|N|+|R|) when there is one arc per node pair, without
rebuilding all initial arc costs. Trigger updates are stored sparsely for each evaluation.
If a candidate has parallel arc choices, the evaluator checks those combinations exactly;
this can take exponential time in the number of parallel choices. The result includes the
selected arc IDs as well as the node cycle.
Classic TSP edge-delta shortcuts are deliberately not used: reversing a segment changes
directed arcs and the order of trigger activation. Genetic algorithms and tabu search are
also viable, but require more tuning and population/memory management; simple local search
can stop at local minima. The exact evaluator prioritizes correctness.

The search uses O(|N|+|A|+|R|) working memory. With no parallel arcs, a compiled evaluation
takes O(|N|+|R|), and a search run takes O(iterations * (|N|+|R|)) time per restart. Finding
the initial feasible cycle uses randomized backtracking and is worst-case exponential. It stops at the optional
wall-clock deadline, so failure to find a cycle within that limit does not prove that none
exists. Brute force is O((|N|-1)! * (|N|+|R|)) time and is for small instances only.

## Coverage of the MESS 2024 document

The implementation covers the computational requirements described in the PDF: it parses
instances, constructs and scores Hamiltonian cycles, and provides a metaheuristic search.
The PDF also describes competition administration: teams of up to three, a short proposal,
portal credentials, uploads, and a leaderboard based on instance scores. Those steps require
participant/team information and access to the portal; they cannot be completed by this
local program.

The PDF does not define the accepted solution-file or stdout format. It says the portal
provides an admissibility/value checker, so the route printed by `main.py` is only a local
display and must not be treated as a confirmed upload format. Before uploading, use that
checker and adapt the output to the exact format it accepts. The public portal page did not
expose readable instructions when checked. Competition deadline in the PDF: 16 October 2024.

Parallel arcs are supported by identifying each selected traversal with its arc ID. When
such arcs are present, exact selection can be much slower because different selections can
activate different triggers.
