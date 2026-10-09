"""Load portable simulation inputs without depending on the visual interface."""

import json
from dataclasses import dataclass
from pathlib import Path

from .grid import Grid, GridError
from .models import Position

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "data" / "search_scenarios"


def validate_event(event: object) -> dict:
    if not isinstance(event, dict):
        raise GridError("An event must be an object.")
    if not isinstance(event.get("id"), str) or not event["id"].strip():
        raise GridError("An event needs a nonempty string ID.")
    if event.get("type") not in ("map", "move"):
        raise GridError("Event type must be 'map' or 'move'.")
    expected = {"id", "type"} | ({"changes"} if event["type"] == "map" else set())
    if not expected <= set(event) or set(event) - expected - {"label"}:
        raise GridError("The event contains missing or unsupported fields.")
    if "label" in event and not isinstance(event["label"], str):
        raise GridError("An event label must be a string.")
    if event["type"] == "map" and not isinstance(event["changes"], list):
        raise GridError("Map changes must be a list of update records.")
    return event


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    description: str
    rows: list[str]
    start: Position
    goal: Position
    events: list[dict]

    def make_grid(self) -> Grid:
        return Grid.from_rows(self.rows)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "rows": list(self.rows), "start": list(self.start), "goal": list(self.goal),
            "events": json.loads(json.dumps(self.events, allow_nan=False)),
        }


def load_scenario(path: str | Path) -> Scenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise GridError(f"Cannot load scenario: {error}") from error
    required = {"id", "title", "description", "rows", "start", "goal", "events"}
    if not isinstance(data, dict) or set(data) != required:
        raise GridError("Scenario fields do not match the documented format.")
    for field in ("id", "title", "description"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise GridError(f"Scenario {field} must be a nonempty string.")
    grid = Grid.from_rows(data["rows"])
    start = grid.validate_position(data["start"], "start")
    goal = grid.validate_position(data["goal"], "goal")
    if not isinstance(data["events"], list):
        raise GridError("Scenario events must be a list.")
    identifiers = set()
    for event in data["events"]:
        validate_event(event)
        if event["id"] in identifiers:
            raise GridError("Scenario event IDs must be unique.")
        identifiers.add(event["id"])
    return Scenario(data["id"], data["title"], data["description"], data["rows"],
                    start, goal, data["events"])


def available_scenarios() -> list[tuple[Path, Scenario]]:
    return [(path, load_scenario(path)) for path in sorted(SCENARIO_DIR.glob("*.json"))]
