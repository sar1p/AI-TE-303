"""Adapter boundary tests using small synthetic engine fixtures only."""

import copy
import math
from types import SimpleNamespace

import pytest

import interface.diagnostics as diagnostics
from interface.diagnostics import DiagnosticState, evaluate_diagnostics


def _valid_fixture_result(status="ok"):
    """Return a schema fixture; it does not implement real diagnosis rules."""
    return {
        "status": status,
        "findings": [
            {"condition": "low_battery", "rule_ids": ["fixture_rule_battery"]}
        ] if status == "ok" else [],
        "rule_trace": [
            {
                "rule_id": "fixture_rule_battery",
                "premises": {"battery_voltage": "low"},
                "conclusion": {"condition": "low_battery"},
                "reason": "Synthetic adapter test fixture.",
            }
        ] if status == "ok" else [],
        "recommendations": [],
        "missing_facts": ["battery_voltage"] if status == "insufficient_evidence" else [],
    }


def _fixture_engine(_facts):
    """Synthetic schema fixture only; this is not the project diagnosis engine."""
    return _valid_fixture_result()


def test_valid_fixture_result_is_ready_and_allows_movement():
    state = evaluate_diagnostics({"battery_voltage": "normal"}, _fixture_engine)

    assert isinstance(state, DiagnosticState)
    assert state.status == "ready"
    assert state.result == _valid_fixture_result()
    assert state.can_move


def test_pause_recommendation_prevents_movement():
    result = _valid_fixture_result()
    result["recommendations"] = [
        {"action": "pause_robot", "reason": "Synthetic pause fixture."}
    ]
    state = evaluate_diagnostics({}, lambda _facts: result)

    assert state.status == "ready"
    assert state.result == result
    assert not state.can_move


@pytest.mark.parametrize("engine_status", ["insufficient_evidence", "invalid_input"])
def test_non_ok_engine_status_prevents_movement(engine_status):
    state = evaluate_diagnostics({}, lambda _facts: _valid_fixture_result(engine_status))

    assert state.status == "ready"
    assert state.result["status"] == engine_status
    assert not state.can_move


def test_missing_engine_module_is_pending(monkeypatch):
    monkeypatch.setattr(diagnostics, "find_spec", lambda _module_name: None)
    state = evaluate_diagnostics({"battery_voltage": None})

    assert state.status == "pending"
    assert state.result is None
    assert "unavailable" in state.message.lower()
    assert not state.can_move


@pytest.mark.parametrize(
    "case",
    [
        "missing_top_level_field",
        "extra_top_level_field",
        "unsupported_status",
        "non_string_status",
        "empty_condition",
        "empty_rule_ids",
        "finding_rule_not_traced",
        "invalid_trace_shape",
        "invalid_recommendation_type",
        "invalid_missing_fact_type",
        "non_finite_nested_value",
    ],
)
def test_malformed_engine_results_fail_closed(case):
    result = _valid_fixture_result()
    if case == "missing_top_level_field":
        del result["missing_facts"]
    elif case == "extra_top_level_field":
        result["debug"] = "not part of the contract"
    elif case == "unsupported_status":
        result["status"] = "probably_ok"
    elif case == "non_string_status":
        result["status"] = []
    elif case == "empty_condition":
        result["findings"][0]["condition"] = ""
    elif case == "empty_rule_ids":
        result["findings"][0]["rule_ids"] = []
    elif case == "finding_rule_not_traced":
        result["findings"][0]["rule_ids"] = ["missing_fixture_rule"]
    elif case == "invalid_trace_shape":
        result["rule_trace"][0]["premises"] = []
    elif case == "invalid_recommendation_type":
        result["recommendations"] = [{"action": "check_drive", "reason": None}]
    elif case == "invalid_missing_fact_type":
        result["missing_facts"] = [17]
    elif case == "non_finite_nested_value":
        result["rule_trace"][0]["premises"] = {"voltage": math.nan}

    state = evaluate_diagnostics({}, lambda _facts: result)

    assert state.status == "error"
    assert state.result is None
    assert state.message
    assert not state.can_move


@pytest.mark.parametrize(
    "facts",
    [None, [], {"reading": math.nan}, {1: "non-string key"}, {"reading": (1, 2)}],
)
def test_non_dictionary_or_non_json_facts_are_rejected_before_call(facts):
    called = False

    def fixture_engine(_raw_facts):
        nonlocal called
        called = True
        return _valid_fixture_result()

    state = evaluate_diagnostics(facts, fixture_engine)

    assert state.status == "error"
    assert state.result is None
    assert not state.can_move
    assert not called


def test_injected_engine_exceptions_return_error_state():
    def broken_fixture(_facts):
        raise RuntimeError("synthetic failure")

    state = evaluate_diagnostics({}, broken_fixture)

    assert state.status == "error"
    assert state.result is None
    assert "call failed" in state.message.lower()
    assert "synthetic failure" in state.message
    assert not state.can_move


def test_present_module_import_failure_returns_error(monkeypatch):
    def fail_import(_module_name):
        raise ModuleNotFoundError("No module named 'fixture_dependency'", name="fixture_dependency")

    monkeypatch.setattr(diagnostics, "find_spec", lambda _module_name: object())
    monkeypatch.setattr(diagnostics.importlib, "import_module", fail_import)

    state = evaluate_diagnostics({})

    assert state.status == "error"
    assert state.result is None
    assert "import failed" in state.message.lower()
    assert "fixture_dependency" in state.message


def test_present_module_without_callable_returns_error(monkeypatch):
    monkeypatch.setattr(diagnostics, "find_spec", lambda _module_name: object())
    monkeypatch.setattr(
        diagnostics.importlib, "import_module", lambda _module_name: SimpleNamespace()
    )

    state = evaluate_diagnostics({})

    assert state.status == "error"
    assert state.result is None
    assert "callable diagnose" in state.message.lower()


def test_engine_mutations_do_not_leak_into_raw_facts_or_returned_result():
    facts = {"battery_voltage": "low", "sensor": {"connected": True}}
    original_facts = copy.deepcopy(facts)
    shared_result = _valid_fixture_result()

    def mutating_fixture(raw_facts):
        raw_facts["derived_condition"] = "fixture_only"
        raw_facts["sensor"]["fixture_note"] = "temporary"
        return shared_result

    state = evaluate_diagnostics(facts, mutating_fixture)

    assert facts == original_facts
    assert state.status == "ready"
    shared_result["findings"][0]["condition"] = "changed outside adapter"
    assert state.result["findings"][0]["condition"] == "low_battery"


def test_corrected_facts_start_a_fresh_fixture_session():
    seen_facts = []

    def correcting_fixture(raw_facts):
        seen_facts.append(copy.deepcopy(raw_facts))
        raw_facts["fixture_derived_fact"] = "temporary"
        if raw_facts.get("battery_voltage") == "low":
            return _valid_fixture_result("ok")
        return _valid_fixture_result("insufficient_evidence")

    first_facts = {"battery_voltage": "low"}
    second_facts = {"battery_voltage": "normal"}
    first = evaluate_diagnostics(first_facts, correcting_fixture)
    second = evaluate_diagnostics(second_facts, correcting_fixture)

    assert first.status == "ready" and first.result["status"] == "ok"
    assert second.status == "ready" and second.result["status"] == "insufficient_evidence"
    assert seen_facts == [
        {"battery_voltage": "low"},
        {"battery_voltage": "normal"},
    ]
    assert first_facts == {"battery_voltage": "low"}
    assert second_facts == {"battery_voltage": "normal"}
