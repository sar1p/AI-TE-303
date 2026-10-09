# Demonstration and evidence guide

## Setup and checks

Use Python 3.12 and run commands from the repository root. In PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -c constraints.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

An existing environment can be reused. Do not recreate it before every run.
On Linux/macOS, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.
Core search and replay use only the standard library; the visual app needs
Streamlit and tests need pytest. `constraints.txt` records the tested versions.

## Visual running sequence

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Open the local URL printed in the terminal. Stop the server with Ctrl+C when
finished. `run_demo.bat` is a Windows shortcut once the environment is installed.

1. Select **Warehouse Corridor Changes** and reset. Show the map, route cost,
   robot, fixed goal, and the actual initial search metrics.
2. Click **Apply next scenario event**. The central aisle closes and the route
   repairs. Compare the new cost and valid detour with A*.
3. Apply the movement event. The robot advances one cell. Open the incremental
   state panel and show one initialization and an updated `k_m`.
4. Continue the remaining events to reopen the aisle. A valid optimal route is
   recomputed from the robot's current position.
5. Select **Unreachable Goal Recovery**, reset, and apply its two events. Show
   `unreachable`, then restoration after the only gap reopens. The goal itself
   is never blocked.
6. Try a manual cell change. Row and column are zero-based. Blocking the robot
   or goal is rejected. Reset before replaying scripted events after manual edits.
7. Inspect **Diagnostics**. While the teammate's engine is absent, the app shows
   **Expert system pending**. Enable the diagnostic safety gate to show that
   missing evidence cannot authorize movement. Search-only mode remains usable.
8. Download actual session JSON from **Evidence & methods**. It contains maps,
   events, computed routes, metrics, raw observations text, and source metadata.

The planner survives ordinary interface reruns, overlay changes, and downloads.
A browser reload or Reset creates a new session. The live UI computes results;
it does not display pretyped benchmark values.

## Headless fallback and benchmark

```powershell
.\.venv\Scripts\python.exe -m search_algorithm.main --output artifacts/single-replay.json
.\.venv\Scripts\python.exe tools/replay_demo.py --output artifacts/demo
.\.venv\Scripts\python.exe tools/benchmark_search.py --output artifacts/benchmark --repeats 5
```

Replay exports actual plan records for all four scenarios. The benchmark writes
`raw.csv` and `summary.json` with initial, repair, and cumulative measurements.
Both exports contain source SHA, worktree cleanliness, environment, versions,
and scenario inputs. A dirty-worktree result is useful during development but
must not be presented as proof of an unchanged committed revision.

## Presentation responsibilities

The lead explains D* Lite's retained state, changed edges, A* comparison, the
independent UCS oracle, suitable use cases, and limitations. The teammate explains
rule sources, forward chaining, traceability, unknown observations, corrected
facts, and multiple findings. See [TEAMMATE_TASKS.md](TEAMMATE_TASKS.md).

After the teammate's module is merged, restart the app, input documented
observations, and demonstrate a real rule chain and its trace. Show `pause_robot`
preventing movement and a corrected input triggering fresh inference. Run their
independent CLI and repeat the full test suite. Do not claim this combined demo
has passed while that module is pending.

## Submission evidence

Preserve actual test output, GitHub Actions links, replay JSON, benchmark CSV/JSON,
and real browser screenshots. Record the screen while presenting the live
scenario changes; the recording is a team task and is not automatically completed
by the screenshot exports. A successful headless run proves execution, while
live input changes and the displayed route demonstrate interactive behavior.

The final combined rehearsal must run from a fresh clone on the teammate's
laptop. Local clean-clone reproduction by the lead is a separate check. Keep large
recordings outside tracked source. Selected verified results live in
`docs/evidence/`; temporary development exports live in ignored `artifacts/`.

## Recovery

- Missing `streamlit` or `pytest`: install the pinned requirements into the same
  interpreter used for the command.
- Port occupied: add `--server.port 8502` and use the printed URL.
- Invalid manual edit or scripted event conflict: reset the scenario.
- Broken diagnostic import or result format: review the Diagnostics error and
  the module contract. Search-only mode is an independent fallback.
- Restore source from Git history or a verified external Git bundle; a virtual
  environment can be rebuilt from the pinned requirement files.
