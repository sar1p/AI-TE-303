"""Persistent, exactly-once simulation actions shared by CLI and Streamlit."""

import json
from copy import deepcopy
from datetime import datetime, timezone

from search_algorithm.astar import astar
from search_algorithm.dstar_lite import DStarLitePlanner
from search_algorithm.grid import GridError
from search_algorithm.scenarios import Scenario, validate_event


class SimulationSession:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.planner = DStarLitePlanner(scenario.make_grid(), scenario.start, scenario.goal)
        self.applied_events: dict[str, str] = {}
        self.records: list[dict] = []
        self.created_at = datetime.now(timezone.utc).isoformat()
        self._record("initial", "Initial planning")

    def _record(self, event_id: str, label: str) -> None:
        self.dstar_result = self.planner.plan()
        self.astar_result = astar(self.planner.grid, self.planner.start, self.planner.goal)
        if (self.dstar_result.status, self.dstar_result.cost) != (
            self.astar_result.status, self.astar_result.cost
        ):
            raise RuntimeError("Route planners disagree on reachability or optimal cost.")
        self.records.append({
            "event_id": event_id, "label": label,
            "map_revision": self.planner.grid.revision,
            "rows": self.planner.grid.to_rows(), "start": list(self.planner.start),
            "goal": list(self.planner.goal), "k_m": self.planner.k_m,
            "initialization_count": self.planner.initialization_count,
            "dstar_lite": self.dstar_result.to_dict(), "astar": self.astar_result.to_dict(),
        })

    def apply_event(self, event: dict, *, movement_allowed: bool = True) -> bool:
        """Apply once; invalid or disallowed events do not become consumed IDs."""
        validate_event(event)
        try:
            signature = json.dumps(event, sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise GridError("Events must be strict JSON-compatible values.") from error
        existing = self.applied_events.get(event["id"])
        if existing is not None:
            if existing != signature:
                raise GridError("The event ID was already used with different content.")
            return False
        if event["type"] == "map":
            self.planner.update_cells(event["changes"])
        else:
            if not movement_allowed:
                raise GridError("Movement is paused by the diagnostic safety gate.")
            if self.dstar_result.status != "found" or len(self.dstar_result.path) < 2:
                raise GridError("No next route step is available; the robot cannot move.")
            self.planner.move_start(self.dstar_result.path[1])
        self.applied_events[event["id"]] = signature
        self._record(event["id"], event.get("label", event["type"]))
        return True

    def replay(self) -> None:
        for event in self.scenario.events:
            self.apply_event(event)

    def to_dict(self) -> dict:
        return deepcopy({
            "schema_version": 1, "scope": "search-only route planning",
            "created_at": self.created_at, "scenario": self.scenario.to_dict(),
            "applied_events": [json.loads(value) for value in self.applied_events.values()],
            "records": self.records,
        })
