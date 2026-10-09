"""Headless scenario replay: python -m search_algorithm.main."""

import argparse
import json
from pathlib import Path

from interface.evidence import environment_metadata
from interface.session import SimulationSession

from .grid import GridError
from .scenarios import SCENARIO_DIR, load_scenario


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay actual D* Lite and A* route results.")
    parser.add_argument("--scenario", type=Path, default=SCENARIO_DIR / "corridor_changes.json")
    parser.add_argument("--output", type=Path, help="Save the strict JSON result to this file.")
    arguments = parser.parse_args()
    try:
        session = SimulationSession(load_scenario(arguments.scenario))
        session.replay()
        report = {"metadata": environment_metadata(), **session.to_dict()}
        serialized = json.dumps(report, indent=2, allow_nan=False)
        if arguments.output:
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(serialized + "\n", encoding="utf-8")
        print(serialized)
        return 0
    except (GridError, OSError) as error:
        parser.exit(2, f"Scenario failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
