#!/usr/bin/env python3
"""Measure persistent D* Lite repairs against repeated A* searches."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Callable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from interface.evidence import environment_metadata
from search_algorithm.astar import astar
from search_algorithm.dstar_lite import DStarLitePlanner
from search_algorithm.grid import Grid, GridError
from search_algorithm.models import SearchResult
from search_algorithm.scenarios import Scenario, available_scenarios


RAW_FIELDS = [
    "scenario_id",
    "repeat",
    "phase",
    "event_id",
    "event_type",
    "event_label",
    "map_revision",
    "start",
    "goal",
    "event_input",
    "grid_rows",
    "dstar_lite_elapsed_ms",
    "dstar_lite_reported_elapsed_ms",
    "dstar_lite_status",
    "dstar_lite_cost",
    "dstar_lite_processed_states",
    "dstar_lite_queue_pops",
    "dstar_lite_queue_pushes",
    "dstar_lite_path",
    "astar_elapsed_ms",
    "astar_reported_elapsed_ms",
    "astar_status",
    "astar_cost",
    "astar_processed_states",
    "astar_queue_pops",
    "astar_queue_pushes",
    "astar_path",
]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark persistent D* Lite repairs and repeated A* searches on "
            "the same scenario maps and movement sequence."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/benchmark"),
        help="output directory (default: artifacts/benchmark, relative to the current directory)",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="independent repetitions per scenario (1 through 100; default: 5)",
    )
    return parser


def _measure(action: Callable[[], SearchResult]) -> tuple[SearchResult, float]:
    started = perf_counter_ns()
    result = action()
    elapsed_ms = (perf_counter_ns() - started) / 1_000_000.0
    return result, elapsed_ms


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _validate_result(result: SearchResult, grid: Grid, start: tuple[int, int], goal: tuple[int, int]) -> None:
    """Check returned paths against the live grid without importing a test oracle."""
    if result.status == "found":
        if result.cost is None or not result.path:
            raise RuntimeError("a found result must include a path and finite cost")
        if result.path[0] != start or result.path[-1] != goal:
            raise RuntimeError("a found path does not connect the requested endpoints")
        for cell in result.path:
            if not grid.contains(cell) or cell in grid.blocked:
                raise RuntimeError(f"a found path enters an invalid or blocked cell: {cell}")
        for left, right in zip(result.path, result.path[1:]):
            if abs(left[0] - right[0]) + abs(left[1] - right[1]) != 1:
                raise RuntimeError("a found path contains a non-cardinal step")
        if result.cost != len(result.path) - 1:
            raise RuntimeError("path cost does not match the unit-cost path length")
        return

    if result.status == "unreachable":
        if result.path or result.cost is not None:
            raise RuntimeError("an unreachable result must not include a path or cost")
        return

    raise RuntimeError(f"unexpected search status: {result.status!r}")


def _check_pair(
    dstar_result: SearchResult,
    astar_result: SearchResult,
    dstar_grid: Grid,
    astar_grid: Grid,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> None:
    if dstar_grid.to_rows() != astar_grid.to_rows():
        raise RuntimeError("D* Lite and A* benchmark maps diverged")
    if dstar_grid.revision != astar_grid.revision:
        raise RuntimeError("D* Lite and A* benchmark map revisions diverged")
    _validate_result(dstar_result, dstar_grid, start, goal)
    _validate_result(astar_result, astar_grid, start, goal)
    if (dstar_result.status, dstar_result.cost) != (astar_result.status, astar_result.cost):
        raise RuntimeError(
            "D* Lite and A* disagree: "
            f"{dstar_result.status}/{dstar_result.cost} versus "
            f"{astar_result.status}/{astar_result.cost}"
        )


def _metric_row(result: SearchResult, elapsed_ms: float) -> dict[str, float | int]:
    return {
        "elapsed_ms": elapsed_ms,
        "processed_states": result.metrics.processed_states,
        "queue_pops": result.metrics.queue_pops,
        "queue_pushes": result.metrics.queue_pushes,
    }


def _write_raw_row(
    writer: csv.DictWriter,
    *,
    scenario: Scenario,
    repeat: int,
    phase: str,
    event_id: str,
    event_type: str,
    event_label: str,
    event_input: Any,
    grid: Grid,
    start: tuple[int, int],
    dstar_result: SearchResult,
    dstar_elapsed_ms: float,
    astar_result: SearchResult,
    astar_elapsed_ms: float,
) -> None:
    writer.writerow(
        {
            "scenario_id": scenario.id,
            "repeat": repeat,
            "phase": phase,
            "event_id": event_id,
            "event_type": event_type,
            "event_label": event_label,
            "map_revision": grid.revision,
            "start": _json(start),
            "goal": _json(scenario.goal),
            "event_input": _json(event_input),
            "grid_rows": _json(grid.to_rows()),
            "dstar_lite_elapsed_ms": f"{dstar_elapsed_ms:.9f}",
            "dstar_lite_reported_elapsed_ms": f"{dstar_result.metrics.elapsed_ms:.9f}",
            "dstar_lite_status": dstar_result.status,
            "dstar_lite_cost": "" if dstar_result.cost is None else dstar_result.cost,
            "dstar_lite_processed_states": dstar_result.metrics.processed_states,
            "dstar_lite_queue_pops": dstar_result.metrics.queue_pops,
            "dstar_lite_queue_pushes": dstar_result.metrics.queue_pushes,
            "dstar_lite_path": _json(dstar_result.path),
            "astar_elapsed_ms": f"{astar_elapsed_ms:.9f}",
            "astar_reported_elapsed_ms": f"{astar_result.metrics.elapsed_ms:.9f}",
            "astar_status": astar_result.status,
            "astar_cost": "" if astar_result.cost is None else astar_result.cost,
            "astar_processed_states": astar_result.metrics.processed_states,
            "astar_queue_pops": astar_result.metrics.queue_pops,
            "astar_queue_pushes": astar_result.metrics.queue_pushes,
            "astar_path": _json(astar_result.path),
        }
    )


def _sum_metrics(rows: list[dict[str, float | int]]) -> dict[str, float | int]:
    return {
        key: sum(row[key] for row in rows)
        for key in ("elapsed_ms", "processed_states", "queue_pops", "queue_pushes")
    }


def _median_metrics(rows: list[dict[str, float | int]]) -> dict[str, float | int]:
    return {
        key: statistics.median(row[key] for row in rows)
        for key in ("elapsed_ms", "processed_states", "queue_pops", "queue_pushes")
    }


def _benchmark_repetition(
    scenario: Scenario,
    repeat: int,
    writer: csv.DictWriter,
) -> dict[str, dict[str, Any]]:
    # Input parsing and the fresh A* baseline grid copy happen before either timer.
    initial_grid = scenario.make_grid()
    astar_grid = initial_grid.clone()
    start = scenario.start
    goal = scenario.goal

    dstar_started = perf_counter_ns()
    dstar = DStarLitePlanner(initial_grid, start, goal)
    dstar_result = dstar.plan()
    dstar_initial_ms = (perf_counter_ns() - dstar_started) / 1_000_000.0

    astar_result, astar_initial_ms = _measure(lambda: astar(astar_grid, start, goal))
    _check_pair(dstar_result, astar_result, dstar.grid, astar_grid, start, goal)

    records: dict[str, dict[str, Any]] = {
        "dstar_lite": {"initial": _metric_row(dstar_result, dstar_initial_ms), "repairs": []},
        "astar": {"initial": _metric_row(astar_result, astar_initial_ms), "repairs": []},
    }
    _write_raw_row(
        writer,
        scenario=scenario,
        repeat=repeat,
        phase="initial",
        event_id="initial",
        event_type="initial",
        event_label="Initial planning",
        event_input={},
        grid=dstar.grid,
        start=start,
        dstar_result=dstar_result,
        dstar_elapsed_ms=dstar_initial_ms,
        astar_result=astar_result,
        astar_elapsed_ms=astar_initial_ms,
    )

    for event in scenario.events:
        event_type = event["type"]
        event_id = event["id"]
        label = event.get("label", event_type)

        if event_type == "map":
            changes = event["changes"]

            dstar_started = perf_counter_ns()
            dstar.update_cells(changes)
            dstar_result = dstar.plan()
            dstar_elapsed_ms = (perf_counter_ns() - dstar_started) / 1_000_000.0

            def update_astar_map_and_search() -> SearchResult:
                astar_grid.apply_changes(changes, protected=(start, goal))
                return astar(astar_grid, start, goal)

            astar_result, astar_elapsed_ms = _measure(update_astar_map_and_search)
        elif event_type == "move":
            if dstar_result.status != "found" or len(dstar_result.path) < 2:
                raise RuntimeError(
                    f"scenario {scenario.id!r} requests movement with no next D* Lite route step"
                )
            # Apply exactly the next step selected from D* Lite to both algorithms.
            next_start = dstar_result.path[1]
            previous_start = start

            dstar_started = perf_counter_ns()
            dstar.move_start(next_start)
            dstar_result = dstar.plan()
            dstar_elapsed_ms = (perf_counter_ns() - dstar_started) / 1_000_000.0

            def validate_move_and_search() -> SearchResult:
                nonlocal start
                if astar_grid.cost(previous_start, next_start) != 1:
                    raise RuntimeError("the shared movement step is not a legal open cardinal move")
                start = astar_grid.validate_position(next_start, "start")
                return astar(astar_grid, start, goal)

            astar_result, astar_elapsed_ms = _measure(validate_move_and_search)
            start = next_start
        else:
            raise RuntimeError(f"scenario {scenario.id!r} has unsupported event type {event_type!r}")

        _check_pair(dstar_result, astar_result, dstar.grid, astar_grid, start, goal)
        dstar_measure = _metric_row(dstar_result, dstar_elapsed_ms)
        astar_measure = _metric_row(astar_result, astar_elapsed_ms)
        records["dstar_lite"]["repairs"].append({"event_id": event_id, **dstar_measure})
        records["astar"]["repairs"].append({"event_id": event_id, **astar_measure})

        _write_raw_row(
            writer,
            scenario=scenario,
            repeat=repeat,
            phase="repair",
            event_id=event_id,
            event_type=event_type,
            event_label=label,
            event_input=event,
            grid=dstar.grid,
            start=start,
            dstar_result=dstar_result,
            dstar_elapsed_ms=dstar_elapsed_ms,
            astar_result=astar_result,
            astar_elapsed_ms=astar_elapsed_ms,
        )

    return records


def _scenario_summary(
    scenario: Scenario,
    repetitions: list[dict[str, dict[str, Any]]],
) -> dict[str, object]:
    algorithm_summaries: dict[str, object] = {}
    for algorithm in ("dstar_lite", "astar"):
        initial_rows = [repeat[algorithm]["initial"] for repeat in repetitions]
        repair_rows = [
            _sum_metrics(repeat[algorithm]["repairs"])
            for repeat in repetitions
        ]
        cumulative_rows = [
            _sum_metrics([repeat[algorithm]["initial"], *repeat[algorithm]["repairs"]])
            for repeat in repetitions
        ]
        per_event: list[dict[str, object]] = []
        for event in scenario.events:
            event_rows = [
                next(
                    row
                    for row in repeat[algorithm]["repairs"]
                    if row["event_id"] == event["id"]
                )
                for repeat in repetitions
            ]
            per_event.append(
                {
                    "event_id": event["id"],
                    "event_type": event["type"],
                    "label": event.get("label", event["type"]),
                    "median": _median_metrics(event_rows),
                }
            )
        algorithm_summaries[algorithm] = {
            "initial_median": _median_metrics(initial_rows),
            "repair_total_median_per_repetition": _median_metrics(repair_rows),
            "cumulative_median_per_repetition": _median_metrics(cumulative_rows),
            "per_event_medians": per_event,
        }
    return {
        "scenario": scenario.to_dict(),
        "repetition_count": len(repetitions),
        "algorithms": algorithm_summaries,
    }


def _run(args: argparse.Namespace) -> tuple[Path, Path, int]:
    scenario_files = available_scenarios()
    if not scenario_files:
        raise ValueError("no named scenario JSON files were found")

    args.output.mkdir(parents=True, exist_ok=True)
    raw_path = args.output / "raw.csv"
    summary_path = args.output / "summary.json"

    summaries: list[dict[str, object]] = []
    raw_row_count = 0
    with raw_path.open("w", newline="", encoding="utf-8") as raw_file:
        writer = csv.DictWriter(raw_file, fieldnames=RAW_FIELDS, extrasaction="raise")
        writer.writeheader()
        for _, scenario in scenario_files:
            repetitions = [
                _benchmark_repetition(scenario, repeat, writer)
                for repeat in range(1, args.repeats + 1)
            ]
            summaries.append(_scenario_summary(scenario, repetitions))
            raw_row_count += args.repeats * (len(scenario.events) + 1)

    document: dict[str, object] = {
        "schema_version": 1,
        "scope": "search-only; diagnostic inference not run",
        "diagnostic_inference_included": False,
        "metadata": environment_metadata(),
        "inputs": [scenario.to_dict() for _, scenario in scenario_files],
        "methodology": {
            "repeats_per_scenario": args.repeats,
            "algorithms": ["persistent_dstar_lite", "repeated_astar"],
            "execution_order": (
                "D* Lite first, A* second for each plan; five repeats are not a claim "
                "of order-neutral microbenchmark."
            ),
            "movement_policy": (
                "For each move event, take the next cell from the current D* Lite route and "
                "apply that same start position to both algorithms. Route-step selection is "
                "outside both timers."
            ),
            "timing_boundaries": {
                "initial_dstar_lite": "planner construction plus initial plan; scenario grid parsing is excluded",
                "initial_astar": "search call on a fresh prebuilt grid clone; scenario parsing and clone are excluded",
                "repair_dstar_lite": "map update or start movement plus plan",
                "repair_astar": "map validation and update or start validation, plus a fresh search",
                "excluded": "scenario loading, route-step choice, output formatting, terminal UI, and file I/O",
            },
            "counting": "State and queue counts are copied from each actual SearchResult; timings use the outer boundaries above.",
            "comparison_checks": "Every result pair must match status and cost, and every found path is checked against its live map.",
            "interpretation": "These are measurements on the included synthetic inputs; they do not establish a universal performance advantage.",
        },
        "raw_csv": raw_path.name,
        "raw_row_count": raw_row_count,
        "scenario_summaries": summaries,
    }
    summary_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return raw_path, summary_path, raw_row_count


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not 1 <= args.repeats <= 100:
        parser.error("--repeats must be between 1 and 100")

    try:
        raw_path, summary_path, row_count = _run(args)
    except (GridError, OSError, TypeError, ValueError, RuntimeError, StopIteration) as exc:
        print(f"Benchmark failed: {exc}", file=sys.stderr)
        return 2

    print(f"Raw measurements ({row_count} rows): {raw_path.resolve()}")
    print(f"Median summary: {summary_path.resolve()}")
    print("Diagnostic inference: not run; benchmark results cover search only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
