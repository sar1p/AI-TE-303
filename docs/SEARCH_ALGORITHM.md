# Search algorithm implementation

## Problem model

One simulated warehouse robot travels to a fixed goal on a finite grid. A cell
is open or blocked. There are four cardinal neighbors and every legal move costs
one. Coordinates are zero-based row/column pairs. The robot has access to the
entire supplied map and receives explicit obstacle updates; this is a simulation
of changing connectivity, not a sensor or obstacle prediction system.

## D* Lite

The method follows the basic formulation in Koenig and Likhachev's
[D* Lite paper](https://idm-lab.org/bib/abstracts/papers/aaai02b.pdf), Figure 3.
It searches backward from the goal and retains two values per cell: `g`, the
current cost estimate, and `rhs`, a one-step lookahead. The goal's `rhs` is zero.
Other cells use the minimum edge cost plus a successor's `g`. Unequal values
identify inconsistent vertices needing repair. The queue orders by:

```text
(min(g, rhs) + Manhattan(current_start, cell) + k_m, min(g, rhs))
```

Moving the start advances `k_m`. Increasing or decreasing edge costs repairs
affected vertices before the shortest-path computation resumes. A route follows
minimum edge-cost-plus-`g` successors. The fixed goal remains unchanged throughout
the session.

Our implementation keeps the `g` and `rhs` dictionaries and the planner object
across every UI rerun and map event. Generation tokens invalidate replaced heap
entries. A still-active entry with an outdated start-dependent key is requeued
using the algorithm's key comparison. These are separate queue cases.

Blocking a cell changes incident edges in both directions. `update_cells` updates
the changed cell and its in-bounds neighbors. Input validation completes before
the map changes. Robot movement is restricted to one legal adjacent step.

## A* and correctness

The baseline starts a new search for each snapshot using Manhattan distance.
Positive unit costs and a consistent heuristic support optimal shortest paths
on this finite model. D* Lite and A* may return different tied shortest routes;
tests compare optimal cost and route validity, not identical geometry.

The UCS oracle in `tests/search_algorithm/oracle.py` reads raw dimensions and
obstacle coordinates. It does not reuse either search implementation's neighbors,
edge costs, or heuristic. Tests cover fixed-seed dynamic maps, blocked/reopened
passages, unreachable recovery, legal movement, protected endpoints, invalid
atomic batches, and zero-length routes. Integration tests also check exactly-once
event IDs and retained state across Streamlit reruns.

## Metrics and comparison boundaries

| Metric | D* Lite | A* |
|---|---|---|
| `processed_states` | Vertices whose `g` is set to `rhs` or reset to infinity during repair | Valid popped states expanded, including the goal |
| `queue_pops` | Actual heap removals, including invalidated entries | Actual heap removals, including outdated entries |
| `queue_pushes` | Insertions during initialization, updates, and the next plan | Insertions during the current fresh search |
| `elapsed_ms` in a search result | Shortest-path repair and route extraction during `plan` | Endpoint validation, fresh search, and route extraction |

D* Lite queue counters include operations pending since the previous plan;
state counters and timing belong to the current plan call. The UI shows actual
current and cumulative work. These counters expose algorithm behavior; they do
not count identical operations across implementations.

`tools/benchmark_search.py` uses wider timing boundaries. Initial D* Lite timing
includes construction; initial A* timing uses a fresh prebuilt grid. Repairs
include map updates or movement validation and the following plan. Parsing,
route-step selection, rendering, and file I/O are excluded. Both algorithms use
the same map and the same start chosen from the current D* Lite route. D* Lite
runs first and A* second; the recorded order is a limitation of this small local
benchmark. Five repetitions produce medians; raw measurements remain available.

## Suitable and unsuitable applications

| Situation | Assessment |
|---|---|
| A robot advances toward one goal while localized obstacles change | D* Lite can reuse prior search work; measure the actual repair cost |
| One small static shortest-path query | A* is simpler and may run faster |
| Many widespread map changes | D* Lite's bookkeeping and repairs may outweigh reuse |
| A new goal for every query | This implementation creates a new planner and loses session reuse |
| Diagonal motion, weighted terrain, continuous coordinates | Unsupported in this implementation |
| Multiple moving robots or time-dependent collisions | Requires a different state model and additional planning logic |

The demo does not establish physical robot reliability. All warehouse maps are
synthetic. Measured performance is tied to the tested source revision, machine,
implementation, and event sequence. See [DEMO_GUIDE.md](DEMO_GUIDE.md) for the
running sequence and evidence files.
