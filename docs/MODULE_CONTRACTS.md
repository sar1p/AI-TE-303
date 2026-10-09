# Module contracts

These contracts define the boundary between two independently runnable modules.
Coordinates are zero-based `(row, column)` pairs, encoded as JSON arrays.

## Route planning

`Grid(height, width, blocked=())` uses finite four-neighbor movement at unit cost.
`Grid.from_rows(rows)` accepts equally sized strings containing `.` and `#`.
Manhattan distance is the heuristic. A blocked cell has impassable incident edges.

`astar(grid, start, goal)` returns a `SearchResult`. Invalid endpoints return
`invalid_input`. `DStarLitePlanner(grid, start, goal)` validates endpoints and raises
`GridError` on invalid construction. It owns a copy of the map so outside changes
cannot silently alter its edge costs. Its public methods are:

- `plan() -> SearchResult`
- `move_start(position)`: one legal adjacent move, or the unchanged current cell.
- `update_cells(changes)`: an atomic batch of `{"cell": [row, column], "blocked": bool}`.

Updates cannot block the current robot or goal. Unknown keys, noninteger/boolean
coordinates, out-of-bounds cells, conflicting duplicate updates, and invalid
types are rejected before mutation. A goal change starts a new planner session.

```json
{
  "status": "found",
  "path": [[0, 0], [0, 1]],
  "cost": 1,
  "metrics": {
    "processed_states": 2,
    "queue_pops": 2,
    "queue_pushes": 3,
    "elapsed_ms": 0.12
  },
  "message": ""
}
```

This is an **illustration of the shape**, not measured output. `status` is `found`,
`unreachable`, or `invalid_input`. A failed result has `path: []` and `cost: null`.
The path includes both endpoints. A valid start equal to the goal has cost zero.
No JSON infinity or NaN is emitted.

## Diagnosis: reserved for the teammate

Implement `expert_system.engine.diagnose(facts: dict[str, object]) -> dict`.
Use a plain JSON-compatible dictionary at this boundary (internal dataclasses
are welcome). Return exactly these top-level fields:

```json
{
  "status": "insufficient_evidence",
  "findings": [],
  "rule_trace": [],
  "recommendations": [],
  "missing_facts": ["battery_voltage"]
}
```

This example documents a format; it is not a currently implemented diagnosis.

- `status`: `ok`, `insufficient_evidence`, or `invalid_input`.
- `findings`: list of `{"condition": str, "rule_ids": [str]}` records.
- `rule_trace`: list of `{"rule_id": str, "premises": dict, "conclusion": dict, "reason": str}` records.
- `recommendations`: list of `{"action": str, "reason": str}` records.
- `missing_facts`: list of observation names.

The input is JSON-compatible. Missing keys and `None` mean unknown, never false.
Each call begins with fresh raw evidence and leaves the input unchanged. Several
suspected conditions may coexist. Corrections replace raw facts and rerun inference;
old derived conclusions must not become input facts. The teammate documents and
validates observation types and rule sources. Rules without domain validation are
labeled `illustrative`.

The agreed recommendation `pause_robot` prevents the simulation's Move robot
action until a fresh valid diagnosis no longer recommends it. Other action IDs
may include `check_power`, `check_drive`, and `check_encoder`. Invalid, unknown,
missing, or broken diagnostic modules cannot produce a successful integrated
robot demonstration. Search remains independently usable in a clearly labeled
search-only simulation.

The adapter validates this format. It never adds rules, diagnoses, certainty
percentages, or recommendations to a missing module.
