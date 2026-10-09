# AI-TE-303

**Warehouse Robot Diagnostics and Dynamic Route Planning**

A two-member Artificial Intelligence coursework project. D* Lite repairs a
warehouse robot's route after map changes and movement. Repeated A* provides a
baseline. A separate rule-based expert system will explain suspected robot faults.

## Implementation status

- Project layout, ownership, and module contracts: established.
- Search algorithms, automated validation, and visual demonstration: in progress.
- Expert system: reserved for the second team member; not implemented yet.

See [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for scope and
[TEAMMATE_TASKS.md](docs/TEAMMATE_TASKS.md) for the reserved work.

## Development setup

Use Python 3.12. From this repository in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Run commands through the virtual environment's Python directly. Activating it
and changing PowerShell's execution policy are unnecessary. Core search will use
only the standard library; Streamlit provides the local visual application.

## Collaboration

Use feature branches, tested commits, pull requests, and merge commits.
The teammate should use their own account and implement their reserved module.
See [CONTRIBUTING.md](CONTRIBUTING.md) and
[MODULE_CONTRACTS.md](docs/MODULE_CONTRACTS.md).

The classroom materials establish the assignment background. The warehouse
theme and advanced algorithm are this team's design choices. Simulation results
do not establish performance or diagnostic reliability on physical robots.

## Method reference

Sven Koenig and Maxim Likhachev, *D* Lite*, AAAI 2002.
[Primary paper](https://idm-lab.org/bib/abstracts/papers/aaai02b.pdf).
Implementation and experiment details will be documented with actual results.
