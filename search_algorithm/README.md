# Route planning

The lead-owned module implements **D\* Lite** and **A\*** on a finite four-neighbor
grid. Each open move costs one; blocked cells are impassable. Coordinates use
zero-based `(row, column)` pairs. Both algorithms return an optimal route or an
explicit `unreachable` result for a valid map.

## Python usage

Run a standalone replay from the repository root:

```powershell
python -m search_algorithm.main --scenario data/search_scenarios/corridor_changes.json
```

```python
from search_algorithm.grid import Grid
from search_algorithm.dstar_lite import DStarLitePlanner
from search_algorithm.astar import astar

grid = Grid(5, 8)
planner = DStarLitePlanner(grid, (2, 0), (2, 7))
initial = planner.plan()
planner.move_start(initial.path[1])
planner.update_cells([{"cell": [2, 4], "blocked": True}])
repaired = planner.plan()
baseline = astar(planner.grid, planner.start, planner.goal)
print(repaired.to_dict())
assert repaired.cost == baseline.cost
```

The core uses the Python standard library. Run its tests with
`python -m pytest tests/search_algorithm -q` after installing the development
requirements. The independent test oracle implements uniform-cost search using
raw dimensions and obstacles; it does not reuse production movement helpers.

## When to use it

D* Lite is useful when the robot's start advances toward a fixed goal and the
map changes during a session. It keeps `g`, `rhs`, its priority queue, and `k_m`
between repairs. A* solves each current snapshot from scratch and is simpler to
use for a single static query.

D* Lite has bookkeeping and memory costs. A first plan, a tiny static map, or
large widespread changes may offer no benefit. No universal speed advantage is
claimed. This implementation does not support diagonal motion, varying finite
edge weights, multiple robots, moving obstacle prediction, or physical control.

The original method supports broader graph models; these restrictions describe
this implementation. A goal change needs a new session. Use `update_cells`, not
direct mutation of the planner's map, to notify it of changed edges.

See [the exact contracts](../docs/MODULE_CONTRACTS.md) and
[the implementation and benchmark guide](../docs/SEARCH_ALGORITHM.md), plus
[Koenig and Likhachev's primary paper](https://idm-lab.org/bib/abstracts/papers/aaai02b.pdf).
