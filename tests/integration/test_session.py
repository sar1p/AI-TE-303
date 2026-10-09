"""Integration contracts for replayable route-planning sessions."""

from copy import deepcopy

import pytest

from interface.session import SimulationSession
from search_algorithm.grid import Grid, GridError
from search_algorithm.scenarios import available_scenarios, load_scenario
from tests.search_algorithm.oracle import ucs_cost


def _assert_result_matches_ucs(grid, result, start, goal):
    expected_cost = ucs_cost(grid, start, goal)
    if expected_cost is None:
        assert result["status"] == "unreachable"
        assert result["path"] == []
        assert result["cost"] is None
        return

    path = [tuple(cell) for cell in result["path"]]
    assert result["status"] == "found"
    assert result["cost"] == expected_cost
    assert path[0] == start
    assert path[-1] == goal
    assert len(path) - 1 == result["cost"]
    for row, column in path:
        assert 0 <= row < grid.height
        assert 0 <= column < grid.width
        assert (row, column) not in grid.blocked
    for first, second in zip(path, path[1:]):
        assert abs(first[0] - second[0]) + abs(first[1] - second[1]) == 1


def _session_snapshot(session):
    return {
        "revision": session.planner.grid.revision,
        "rows": session.planner.grid.to_rows(),
        "start": session.planner.start,
        "goal": session.planner.goal,
        "k_m": session.planner.k_m,
        "records": deepcopy(session.records),
        "applied_events": deepcopy(session.applied_events),
        "dstar_result": session.dstar_result.to_dict(),
        "astar_result": session.astar_result.to_dict(),
        "g": dict(session.planner.g),
        "rhs": dict(session.planner.rhs),
    }


def _scenario(scenario_id):
    for _, scenario in available_scenarios():
        if scenario.id == scenario_id:
            return scenario
    raise AssertionError(f"Missing scenario: {scenario_id}")


def test_all_named_scenarios_replay_to_ucs_optimal_routes():
    scenarios = available_scenarios()
    assert len(scenarios) == 4

    for _, scenario in scenarios:
        session = SimulationSession(scenario)
        session.replay()

        assert len(session.records) == 1 + len(scenario.events)
        assert session.planner.initialization_count == 1
        for record in session.records:
            grid = Grid.from_rows(record["rows"])
            start = tuple(record["start"])
            goal = tuple(record["goal"])
            _assert_result_matches_ucs(grid, record["dstar_lite"], start, goal)
            _assert_result_matches_ucs(grid, record["astar"], start, goal)
            assert record["initialization_count"] == 1


def test_unreachable_goal_recovers_after_reopening_the_only_gap():
    scenario = _scenario("unreachable-recovery")
    session = SimulationSession(scenario)
    assert session.records[-1]["dstar_lite"]["status"] == "found"

    session.apply_event(scenario.events[0])
    closed = session.records[-1]["dstar_lite"]
    _assert_result_matches_ucs(
        session.planner.grid, closed, session.planner.start, session.planner.goal
    )
    assert closed["status"] == "unreachable"

    session.apply_event(scenario.events[1])
    reopened = session.records[-1]["dstar_lite"]
    _assert_result_matches_ucs(
        session.planner.grid, reopened, session.planner.start, session.planner.goal
    )
    assert reopened["status"] == "found"


def test_duplicate_event_is_exactly_once_and_changes_nothing():
    scenario = _scenario("corridor-changes")
    session = SimulationSession(scenario)
    event = scenario.events[0]
    assert session.apply_event(event)
    before = _session_snapshot(session)

    assert not session.apply_event(event)

    assert _session_snapshot(session) == before


def test_conflicting_event_id_is_rejected_and_failed_new_id_can_retry():
    scenario = _scenario("corridor-changes")
    session = SimulationSession(scenario)
    original_event = scenario.events[0]
    assert session.apply_event(original_event)
    before_conflict = _session_snapshot(session)
    changed_content = deepcopy(original_event)
    changed_content["changes"][0]["blocked"] = False

    with pytest.raises(GridError):
        session.apply_event(changed_content)
    assert _session_snapshot(session) == before_conflict

    invalid_new_id = {
        "id": "retryable-manual-edit",
        "type": "map",
        "changes": [
            {"cell": [0, 0], "blocked": True},
            {"cell": [99, 99], "blocked": True},
        ],
    }
    before_invalid = _session_snapshot(session)
    with pytest.raises(GridError):
        session.apply_event(invalid_new_id)
    assert _session_snapshot(session) == before_invalid
    assert "retryable-manual-edit" not in session.applied_events

    corrected = {
        "id": "retryable-manual-edit",
        "type": "map",
        "changes": [{"cell": [0, 0], "blocked": True}],
    }
    assert session.apply_event(corrected)
    assert "retryable-manual-edit" in session.applied_events
    assert session.planner.grid.to_rows()[0][0] == "#"


@pytest.mark.parametrize("protected_cell", ["start", "goal"])
def test_invalid_map_batch_and_protected_cells_leave_session_unchanged(protected_cell):
    scenario = _scenario("corridor-changes")
    session = SimulationSession(scenario)
    protected = session.planner.start if protected_cell == "start" else session.planner.goal
    event = {
        "id": f"invalid-protected-{protected_cell}",
        "type": "map",
        "changes": [
            {"cell": [0, 0], "blocked": True},
            {"cell": list(protected), "blocked": True},
        ],
    }
    before = _session_snapshot(session)

    with pytest.raises(GridError):
        session.apply_event(event)

    assert _session_snapshot(session) == before
    assert event["id"] not in session.applied_events


def test_disallowed_movement_leaves_session_unchanged_and_event_unconsumed():
    scenario = _scenario("movement-reuse")
    session = SimulationSession(scenario)
    event = scenario.events[0]
    before = _session_snapshot(session)

    with pytest.raises(GridError):
        session.apply_event(event, movement_allowed=False)

    assert _session_snapshot(session) == before
    assert event["id"] not in session.applied_events


def test_planner_and_search_tables_survive_map_and_movement_events():
    scenario = _scenario("corridor-changes")
    session = SimulationSession(scenario)
    planner = session.planner
    g_table = planner.g
    rhs_table = planner.rhs
    event_count = len(session.records)

    session.apply_event(scenario.events[0])
    session.apply_event(scenario.events[1])

    assert session.planner is planner
    assert planner.g is g_table
    assert planner.rhs is rhs_table
    assert planner.initialization_count == 1
    assert len(session.records) == event_count + 2


def test_manual_map_edit_is_exported_and_export_is_a_deep_copy():
    scenario = _scenario("corridor-changes")
    session = SimulationSession(scenario)
    event = {
        "id": "manual-map-edit-fixture",
        "type": "map",
        "label": "Synthetic integration test map edit",
        "changes": [{"cell": [0, 0], "blocked": True}],
    }
    session.apply_event(event)

    exported = session.to_dict()
    assert exported["records"][-1]["rows"][0][0] == "#"
    assert exported["scenario"]["rows"][0][0] == "."
    assert exported["records"][-1]["map_revision"] == 1

    exported["records"][-1]["rows"][0] = "mutated export"
    exported["scenario"]["events"].clear()
    assert session.records[-1]["rows"][0][0] == "#"
    assert session.scenario.events
    assert session.to_dict()["records"][-1]["rows"][0][0] == "#"
