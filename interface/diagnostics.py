"""Validate and safely adapt the optional expert-system module."""

from __future__ import annotations

import copy
import importlib
import math
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any, Callable, Literal


AdapterStatus = Literal["pending", "ready", "error"]
DiagnosisFunction = Callable[[dict[str, Any]], dict[str, Any]]

_ENGINE_MODULE = "expert_system.engine"
_RESULT_KEYS = {
    "status",
    "findings",
    "rule_trace",
    "recommendations",
    "missing_facts",
}
_ENGINE_STATUSES = {"ok", "insufficient_evidence", "invalid_input"}


@dataclass
class DiagnosticState:
    """The validated state of one fresh diagnosis evaluation."""

    status: AdapterStatus
    message: str
    result: dict[str, Any] | None = None

    @property
    def can_move(self) -> bool:
        """Allow movement only after a valid result with no pause recommendation."""
        if self.status != "ready" or type(self.result) is not dict:
            return False
        if self.result.get("status") != "ok":
            return False
        recommendations = self.result.get("recommendations")
        if type(recommendations) is not list:
            return False
        if any(
            type(item) is not dict
            or set(item) != {"action", "reason"}
            or type(item["action"]) is not str
            or type(item["reason"]) is not str
            for item in recommendations
        ):
            return False
        return not any(item["action"] == "pause_robot" for item in recommendations)


def _is_json_value(value: Any, active: set[int] | None = None) -> bool:
    """Check strict JSON values, string object keys, finite numbers, and no cycles."""
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) not in (list, dict):
        return False

    if active is None:
        active = set()
    identity = id(value)
    if identity in active:
        return False
    active.add(identity)
    try:
        if type(value) is list:
            return all(_is_json_value(item, active) for item in value)
        return all(
            type(key) is str and _is_json_value(item, active)
            for key, item in value.items()
        )
    finally:
        active.remove(identity)


def _record(value: Any, keys: set[str]) -> bool:
    return type(value) is dict and set(value) == keys


def _validate_result(value: Any) -> str | None:
    """Return an English validation error, or None for a valid engine result."""
    if type(value) is not dict:
        return "Diagnosis engine must return a dictionary."
    if set(value) != _RESULT_KEYS:
        return "Diagnosis result must contain exactly the agreed top-level fields."
    if not _is_json_value(value):
        return "Diagnosis result must contain only finite JSON-compatible values."
    status = value["status"]
    if type(status) is not str or status not in _ENGINE_STATUSES:
        return "Diagnosis result has an unsupported status."
    if type(value["findings"]) is not list:
        return "Diagnosis findings must be a list."
    if type(value["rule_trace"]) is not list:
        return "Diagnosis rule trace must be a list."
    if type(value["recommendations"]) is not list:
        return "Diagnosis recommendations must be a list."
    if type(value["missing_facts"]) is not list or any(
        type(fact) is not str for fact in value["missing_facts"]
    ):
        return "Diagnosis missing facts must be a list of strings."

    traced_rule_ids: set[str] = set()
    for item in value["rule_trace"]:
        if not _record(item, {"rule_id", "premises", "conclusion", "reason"}):
            return "Each diagnosis trace entry must contain the agreed fields."
        if type(item["rule_id"]) is not str or not item["rule_id"]:
            return "Each diagnosis trace rule ID must be a nonempty string."
        if type(item["premises"]) is not dict or type(item["conclusion"]) is not dict:
            return "Diagnosis trace premises and conclusions must be dictionaries."
        if type(item["reason"]) is not str:
            return "Each diagnosis trace reason must be a string."
        traced_rule_ids.add(item["rule_id"])

    for item in value["findings"]:
        if not _record(item, {"condition", "rule_ids"}):
            return "Each diagnosis finding must contain condition and rule IDs."
        rule_ids = item["rule_ids"]
        if type(item["condition"]) is not str or not item["condition"]:
            return "Each diagnosis condition must be a nonempty string."
        if type(rule_ids) is not list or not rule_ids or any(
            type(rule_id) is not str or not rule_id for rule_id in rule_ids
        ):
            return "Each diagnosis finding must list nonempty rule IDs."
        if any(rule_id not in traced_rule_ids for rule_id in rule_ids):
            return "Every finding rule ID must appear in the diagnosis trace."

    for item in value["recommendations"]:
        if not _record(item, {"action", "reason"}):
            return "Each diagnosis recommendation must contain action and reason."
        if type(item["action"]) is not str or type(item["reason"]) is not str:
            return "Diagnosis recommendation actions and reasons must be strings."
    return None


def _load_diagnose() -> tuple[DiagnosisFunction | None, DiagnosticState | None]:
    """Load the optional engine, distinguishing absence from broken imports."""
    try:
        spec = find_spec(_ENGINE_MODULE)
    except ModuleNotFoundError as error:
        if error.name in {"expert_system", _ENGINE_MODULE}:
            return None, DiagnosticState(
                "pending", "Diagnostic module is unavailable; diagnosis is pending."
            )
        return None, DiagnosticState(
            "error",
            f"Diagnostic module import failed: {type(error).__name__}: {error}",
        )
    except Exception as error:
        return None, DiagnosticState(
            "error",
            f"Diagnostic module discovery failed: {type(error).__name__}: {error}",
        )

    if spec is None:
        return None, DiagnosticState(
            "pending", "Diagnostic module is unavailable; diagnosis is pending."
        )

    try:
        module = importlib.import_module(_ENGINE_MODULE)
    except Exception as error:
        return None, DiagnosticState(
            "error",
            f"Diagnostic module import failed: {type(error).__name__}: {error}",
        )

    diagnose = getattr(module, "diagnose", None)
    if not callable(diagnose):
        return None, DiagnosticState(
            "error", "Diagnostic module does not provide a callable diagnose function."
        )
    return diagnose, None


def evaluate_diagnostics(
    facts: dict[str, Any], diagnose: DiagnosisFunction | None = None
) -> DiagnosticState:
    """Evaluate a fresh raw-facts copy and validate the returned JSON contract."""
    if type(facts) is not dict:
        return DiagnosticState("error", "Diagnosis facts must be a dictionary.")
    if not _is_json_value(facts):
        return DiagnosticState(
            "error", "Diagnosis facts must contain only finite JSON-compatible values."
        )
    try:
        raw_facts = copy.deepcopy(facts)
    except Exception as error:
        return DiagnosticState(
            "error", f"Diagnosis facts could not be copied: {type(error).__name__}: {error}"
        )

    if diagnose is None:
        diagnose, unavailable = _load_diagnose()
        if unavailable is not None:
            return unavailable
    elif not callable(diagnose):
        return DiagnosticState("error", "Injected diagnosis engine must be callable.")

    try:
        engine_result = diagnose(raw_facts)
    except Exception as error:
        return DiagnosticState(
            "error", f"Diagnosis engine call failed: {type(error).__name__}: {error}"
        )

    validation_error = _validate_result(engine_result)
    if validation_error is not None:
        return DiagnosticState("error", validation_error)
    try:
        result = copy.deepcopy(engine_result)
    except Exception as error:
        return DiagnosticState(
            "error", f"Diagnosis result could not be copied: {type(error).__name__}: {error}"
        )

    return DiagnosticState("ready", "Diagnosis result validated.", result)
