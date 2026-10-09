#!/usr/bin/env python3
"""Replay the named warehouse search scenarios and save their actual outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from interface.evidence import environment_metadata
from interface.session import SimulationSession
from search_algorithm.scenarios import Scenario, available_scenarios, load_scenario


def _source_label(path: Path) -> str:
    """Keep project inputs portable and avoid recording external absolute paths."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.name


def _selected_scenarios(scenario_arg: str | None) -> list[tuple[str, Scenario]]:
    if scenario_arg is None:
        return [(_source_label(path), scenario) for path, scenario in available_scenarios()]

    requested = Path(scenario_arg).expanduser()
    if requested.is_absolute():
        candidate = requested
    else:
        from_cwd = requested.resolve()
        from_project = (PROJECT_ROOT / requested).resolve()
        candidate = from_cwd if from_cwd.is_file() else from_project
    scenario = load_scenario(candidate)
    return [(_source_label(candidate), scenario)]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replay the search-only warehouse scenarios and save the actual run "
            "records as strict JSON. No diagnostic inference is included."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/demo"),
        help="output directory (default: artifacts/demo, relative to the current directory)",
    )
    parser.add_argument(
        "--scenario",
        help="optional scenario JSON file; defaults to every named scenario",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    try:
        selected = _selected_scenarios(args.scenario)
        if not selected:
            raise ValueError("no scenario JSON files were found")

        runs: list[dict[str, object]] = []
        for source, scenario in selected:
            session = SimulationSession(scenario)
            session.replay()
            run = session.to_dict()
            run["scope"] = "search-only; diagnostic inference not run"
            run["diagnostic_inference_included"] = False
            run["source_file"] = source
            runs.append(run)

        document: dict[str, object] = {
            "schema_version": 1,
            "scope": "search-only; diagnostic inference not run",
            "diagnostic_inference_included": False,
            "metadata": environment_metadata(),
            "selection": "all_named_scenarios" if args.scenario is None else "single_file",
            "scenario_count": len(runs),
            "runs": runs,
        }
        serialized = json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )

        args.output.mkdir(parents=True, exist_ok=True)
        output_file = args.output / "replay.json"
        output_file.write_text(serialized + "\n", encoding="utf-8")
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"Replay failed: {exc}", file=sys.stderr)
        return 2

    print(f"Replay JSON: {output_file.resolve()}")
    for run in runs:
        records = run["records"]
        last = records[-1] if records else {}
        result = last.get("dstar_lite", {})
        print(
            f"{run['scenario']['id']}: {len(records)} recorded plans; "
            f"final status={result.get('status')}, cost={result.get('cost')}"
        )
    print("Diagnostic inference: not run; this artifact contains search results only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
