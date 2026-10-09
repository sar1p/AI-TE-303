"""Streamlit integration checks for session persistence and safety gating."""

from copy import deepcopy
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import interface.diagnostics as diagnostics
from interface.diagnostics import DiagnosticState


def _pending_fixture(_facts):
    """Keep pending-state UI checks independent of the teammate engine."""
    return DiagnosticState("pending", "Synthetic pending-state AppTest fixture.")


def _run(app):
    app.run(timeout=20)
    assert not app.exception, [entry.message for entry in app.exception]
    return app


def _simulation(app):
    return app.session_state["simulation"]


def _select_scenario(app, scenario_id):
    app.selectbox(key="scenario_choice").set_value(scenario_id)
    return _run(app)


def _click(app, key):
    app.button(key=key).click()
    return _run(app)


def test_app_session_persists_across_reruns_and_controls_dynamic_scenarios(monkeypatch):
    monkeypatch.setattr(diagnostics, "evaluate_diagnostics", _pending_fixture)
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    app = _run(AppTest.from_file(app_path))
    assert _simulation(app).planner.initialization_count == 1

    app = _select_scenario(app, "corridor-changes")
    session = _simulation(app)
    planner = session.planner
    g_table = planner.g
    rhs_table = planner.rhs
    initial_records = deepcopy(session.records)

    app.radio(key="route_overlay").set_value("A*")
    app = _run(app)
    assert _simulation(app) is session
    assert session.planner is planner
    assert planner.g is g_table
    assert planner.rhs is rhs_table
    assert session.records == initial_records
    assert planner.initialization_count == 1

    app = _click(app, "next_event")
    assert _simulation(app) is session
    assert planner.grid.revision == 1
    assert len(session.records) == len(initial_records) + 1
    assert session.records[-1]["event_id"] == "corridor-close-center-aisle"

    previous_start = planner.start
    previous_count = len(session.records)
    assert not app.button(key="move_robot").disabled
    app = _click(app, "move_robot")
    assert _simulation(app) is session
    assert planner.start != previous_start
    assert abs(planner.start[0] - previous_start[0]) + abs(
        planner.start[1] - previous_start[1]
    ) == 1
    assert len(session.records) == previous_count + 1
    assert planner.initialization_count == 1

    app = _select_scenario(app, "unreachable-recovery")
    session = _simulation(app)
    assert session.dstar_result.status == "found"
    app = _click(app, "next_event")
    assert session.dstar_result.status == "unreachable"
    app = _click(app, "next_event")
    assert session.dstar_result.status == "found"
    assert len(session.records) == 3
    assert session.planner.initialization_count == 1

    app = _select_scenario(app, "movement-reuse")
    session = _simulation(app)
    assert session.dstar_result.status == "found"
    initial_records = deepcopy(session.records)
    app.toggle(key="diagnostic_gate").set_value(True)
    app = _run(app)

    assert _simulation(app) is session
    assert any("expert system pending" in item.value.lower() for item in app.info)
    assert app.button(key="next_event").disabled
    assert app.button(key="move_robot").disabled
    assert session.planner.start == tuple(session.scenario.start)
    assert session.records == initial_records
    assert session.planner.initialization_count == 1


@pytest.mark.parametrize("raw_facts", ["{", '{"voltage": NaN}', "[]"])
def test_invalid_observation_json_fails_closed_without_map_mutation(raw_facts):
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    app = _run(AppTest.from_file(app_path))
    session = _simulation(app)
    before = {
        "revision": session.planner.grid.revision,
        "rows": session.planner.grid.to_rows(),
        "start": session.planner.start,
        "records": deepcopy(session.records),
        "applied_events": deepcopy(session.applied_events),
    }

    app.text_area(key="raw_facts").set_value(raw_facts)
    app.toggle(key="diagnostic_gate").set_value(True)
    app = _run(app)

    assert app.error
    assert app.button(key="move_robot").disabled
    assert _simulation(app) is session
    assert session.planner.grid.revision == before["revision"]
    assert session.planner.grid.to_rows() == before["rows"]
    assert session.planner.start == before["start"]
    assert session.records == before["records"]
    assert session.applied_events == before["applied_events"]


def test_form_cannot_block_goal_and_leaves_session_unchanged(monkeypatch):
    monkeypatch.setattr(diagnostics, "evaluate_diagnostics", _pending_fixture)
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    app = _run(AppTest.from_file(app_path))
    app = _select_scenario(app, "movement-reuse")
    session = _simulation(app)
    before = {
        "revision": session.planner.grid.revision,
        "rows": session.planner.grid.to_rows(),
        "start": session.planner.start,
        "goal": session.planner.goal,
        "records": deepcopy(session.records),
        "applied_events": deepcopy(session.applied_events),
    }

    next(widget for widget in app.number_input if widget.label == "Row").set_value(
        session.planner.goal[0]
    )
    next(widget for widget in app.number_input if widget.label == "Column").set_value(
        session.planner.goal[1]
    )
    next(widget for widget in app.selectbox if widget.label == "Cell state").set_value(
        "Blocked"
    )
    next(
        widget for widget in app.button if widget.label == "Apply cell change"
    ).click()
    app = _run(app)

    assert any("protected cell" in error.value.lower() for error in app.error)
    assert session.planner.grid.revision == before["revision"]
    assert session.planner.grid.to_rows() == before["rows"]
    assert session.planner.start == before["start"]
    assert session.planner.goal == before["goal"]
    assert session.records == before["records"]
    assert session.applied_events == before["applied_events"]
