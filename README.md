# AI-TE-303

**Warehouse Robot Diagnostics and Dynamic Route Planning**

[![Python validation](https://github.com/sar1p/AI-TE-303/actions/workflows/tests.yml/badge.svg)](https://github.com/sar1p/AI-TE-303/actions/workflows/tests.yml)

A two-member Artificial Intelligence coursework project. D* Lite repairs a
warehouse robot's route after map changes and movement. Repeated A* provides a
baseline. A separate rule-based expert system will explain suspected robot faults.

## Implementation status

- Project layout, ownership, and module contracts: established.
- D* Lite, A*, validated maps, and independent search tests: implemented.
- Streamlit demonstration, scenario replay, benchmark exports, and diagnostic adapter: implemented.
- Expert system: reserved for the second team member; not implemented yet.

See [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for scope and
[TEAMMATE_TASKS.md](docs/TEAMMATE_TASKS.md) for the reserved work.

## Development setup

Use Python 3.12. From this repository in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -c constraints.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Run commands through the virtual environment's Python directly. Activating it
and changing PowerShell's execution policy are unnecessary. Core search will use
only the standard library; Streamlit provides the local visual application.

After setup, Windows users can double-click `run_demo.bat`. Stop the server with
Ctrl+C. See [DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for the live presentation sequence.

## Run without the interface

```powershell
.\.venv\Scripts\python.exe -m search_algorithm.main --output artifacts/single-replay.json
.\.venv\Scripts\python.exe tools/replay_demo.py --output artifacts/demo
.\.venv\Scripts\python.exe tools/benchmark_search.py --output artifacts/benchmark --repeats 5
```

Four synthetic scenarios cover a blocked/reopened aisle, movement with retained
search state, unreachable-goal recovery, and widespread map changes. Exports
contain actual inputs, computed routes, metrics, source SHA, and environment.
Development exports go to ignored `artifacts/`.

Verified running results, source metadata, real screenshots, and clean-clone
checks are in [docs/evidence/](docs/evidence/README.md).

![Live route repair](docs/evidence/route-demo.jpg)

## Why these methods

| Method | Role | Limits |
|---|---|---|
| D* Lite | Repair routes while the start moves toward a fixed goal and map connectivity changes | Initialization and extensive changes can cost more than reuse saves |
| A* | Fresh shortest-path baseline for the current map | Repeats search after each update |
| UCS / Dijkstra | Independent optimal-cost oracle in tests | Used for correctness, not the interactive planner |
| Forward-chaining expert system | Teammate's pending fault explanation module | Depends on documented rules and evidence; no measured accuracy claimed |

The grid supports four-neighbor unit-cost movement. Weighted terrain, diagonal
motion, multiple robots, and physical control are outside this implementation.
See [SEARCH_ALGORITHM.md](docs/SEARCH_ALGORITHM.md) for algorithm details,
metric definitions, benchmark boundaries, and suitable/unsuitable uses.

The diagnostic safety gate requires a valid `ok` diagnosis without `pause_robot`
before allowing movement. A missing engine is shown as pending. The search-only
simulation remains independently usable. Adapter tests use synthetic contract
fixtures; they do not constitute the real expert-system implementation.

## Collaboration

Use feature branches, tested commits, pull requests, and merge commits.
The teammate should use their own account and implement their reserved module.
See [CONTRIBUTING.md](CONTRIBUTING.md) and
[MODULE_CONTRACTS.md](docs/MODULE_CONTRACTS.md).

The reserved teammate task is tracked in
[issue #3](https://github.com/sar1p/AI-TE-303/issues/3). Collaborator access will be
added after the teammate's GitHub username is confirmed.

The classroom materials establish the assignment background. The warehouse
theme and advanced algorithm are this team's design choices. Simulation results
do not establish performance or diagnostic reliability on physical robots.

## Method reference

Sven Koenig and Maxim Likhachev, *D* Lite*, AAAI 2002.
[Primary paper](https://idm-lab.org/bib/abstracts/papers/aaai02b.pdf).
Implementation and experiment details will be documented with actual results.
