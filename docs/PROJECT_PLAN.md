# AI-TE-303 Project Plan

Planning date: Friday, October 9, 2026. Working delivery target: Sunday, October 11, 2026, Asia/Jakarta. The exact submission time is unconfirmed.

Status: accepted implementation plan. Project setup has begun. The README and evidence guide track implemented and verified features; future work below does not claim completed results.

## Project and scope

Proposed application title: **Warehouse Robot Diagnostics and Dynamic Route Planning**.

Repository name: `AI-TE-303`. Owner: `sar1p`. Use a dedicated checkout of this repository rather than the parent folder containing course materials.

The team has two members. The lead owns route planning, the application, and integration. The teammate owns the expert system, its knowledge base, tests, and diagnostic explanations. All repository text, identifiers, comments, interface labels, documentation, commits, PRs, and workflow names use English.

The application runs locally in Python and simulates one warehouse robot. It has two separately runnable modules and one shared visual demonstration. No physical robot is required.

| Module | Required first version | Purpose |
|---|---|---|
| Expert system | External IF-THEN rules, forward chaining, explanation trace, unknown evidence, and recalculation after corrected facts | Explain possible robot faults and the observations behind each finding |
| Search | D* Lite with persistent incremental search state; repeated A* for comparison; UCS/Dijkstra as an independent correctness oracle | Repair a route after the robot moves or the map changes |
| Demo | Local Streamlit interface, named scenarios, step controls, blocked/unblocked cells, visible diagnoses and route metrics | Let the presenter change inputs and show actual computed behavior |
| Evidence | Automated tests, scenario replay, real exported results, clean-clone reproduction, and a screen recording | Demonstrate both correctness and reproducibility |

Bayesian reasoning is an optional extension after both required modules pass their tests and the complete demo works. Its parameters would need documented provenance. It is not required for the first release, and it is already mentioned in the supplied expert-system syllabus. No diagnosis percentages will be invented.

The first version excludes cloud deployment, chatbot APIs, physical motor control, multiple robots, continuous-space motion, and time-dependent collision prediction. These features are outside the two-day implementation target.

## Requirements and proposals

The supplied classroom notes describe a group repository, a manager/main branch, developer branches, module folders, and README content covering introduction, dependencies, usage, and running results. The expert-system slides describe a knowledge base, IF-THEN rules, and an inference engine. The search materials and LMS snapshot cover the established search algorithms used as our baselines.

D* Lite, the warehouse theme, the module split, the interface, and the acceptance tests below are project proposals. They are not additional lecturer requirements. The current deadline estimate comes from the user. Historical dates displayed in the LMS snapshot do not establish this assignment's current deadline.

## Module ownership

| Owner | Files and responsibilities | Presentation responsibility |
|---|---|---|
| Lead, working with the assistant | Project bootstrap, `search_algorithm/`, `tests/search_algorithm/`, `data/search_scenarios/`, `app.py`, CI, shared contracts, and integrated replay/export tools | D* Lite, A* comparison, route correctness, and application integration |
| Teammate | `expert_system/`, `tests/expert_system/`, `data/diagnostic_scenarios/`, and `docs/EXPERT_SYSTEM.md` | Rules, inference trace, missing evidence, limitations, and corrected-fact demonstration |
| Both | Cross-review, integration acceptance, README accuracy, and a final rehearsal on the teammate's laptop | Each explains their own work and answers questions about the shared demo |

Reserve the teammate's implementation for the teammate. The lead supplies contracts, examples of the expected data shape, and review support. While that module is pending, the interface must state that status rather than return simulated completed diagnoses.

Use feature branches in one shared repository. The teammate accepts a collaborator invitation and commits/pushes through their own GitHub account. A fork is optional and adds synchronization work; the proposed group workflow uses collaborator access and branches.

## Module contract summary

The implementation boundary is frozen in [MODULE_CONTRACTS.md](MODULE_CONTRACTS.md). That document is authoritative for exact data types. This section summarizes the intended behavior.

### Diagnosis

`diagnose(facts: dict[str, object]) -> DiagnosisResult`

- Facts use documented names and types. An absent observation or `None` means unknown, never false.
- The function does not mutate the caller's facts. Each call starts a fresh inference session from the supplied raw observations.
- The result contains `status`, `findings`, `rule_trace`, `recommendations`, and `missing_facts`.
- Status is one of `ok`, `insufficient_evidence`, or `invalid_input`. Several supported findings may coexist; the engine does not assume that only one fault is possible.
- Trace entries identify the rule ID, observed/derived premises, produced conclusion, and English reason. Unsupported conclusions are excluded.
- Findings identify suspected conditions, not a claim of field-validated certainty. Rules record their source and validation status. Synthetic rules are marked `illustrative`.
- When a fact is corrected, the application replaces the raw observation and calls `diagnose` again. It must not feed old derived conclusions back into the next session.
- Contradictory representations of the same observation and invalid values produce a clear validation result. Document the exact combinations that are invalid; do not treat every unusual sensor combination as a contradiction.
- Recommendations can include English action IDs such as `pause_robot`, `check_power`, `check_drive`, and `check_encoder`. The module never imports the route planner or interface.

Initial proposed scope: four suspected conditions, approximately eight observation types, and 8-12 meaningful rules. The teammate may refine that scope before implementation. Initial conditions are low battery, drive blockage, motor connection problems, and encoder signal problems. These are simulation cases until domain sources or expert review support the rules and thresholds.

### Route planning

- `DStarLitePlanner(grid, start, goal)` creates a search session.
- `move_start(position)` advances the current start without discarding the search session.
- `update_cells(changes)` applies a validated map update once.
- `plan() -> SearchResult` returns a route or an explicit unreachable result, plus metrics.
- `astar(grid, start, goal)` and the test oracle solve each current map snapshot independently.
- Results distinguish invalid input from an unreachable valid goal. A route contains its start and goal; each adjacent pair represents one valid move. Start equal to goal produces a one-cell route of cost zero.

Freeze the serialized result fields: `status` is `found`, `unreachable`, or `invalid_input`; `path` is a list of `[row, column]` integer pairs; `cost` is an integer for a found route and `null` otherwise. Unreachable and invalid results use an empty path. `metrics` contains nonnegative `processed_states`, `queue_pops`, `queue_pushes`, and finite `elapsed_ms`; the processing-counter definition is documented for each algorithm. Include the current map revision in exported replay records. Do not serialize infinite costs as nonstandard JSON numbers.

Reject coordinates outside the grid, blocked starts/goals, malformed updates, and an update that blocks the currently occupied start or fixed goal. Validate a start equal to goal before returning its zero-cost route. A goal is made unreachable by blocking its access, rather than blocking the goal cell itself. Reject an invalid event without partially mutating the map or search session.

The first version uses a finite four-neighbor grid, unit movement costs, blocked cells represented as impassable edges, Manhattan distance, and a fixed goal within a session. Search state includes `g`, `rhs`, the priority queue, and the start/key bookkeeping, and survives map changes. Changed edges update the affected vertices before repairing the path. A changed goal creates a new session. Follow the primary D* Lite pseudocode and handle outdated queue entries correctly.

Persist the planner in Streamlit session state between interface reruns. Apply map events once using event IDs or an equivalent explicit mechanism. A page reload may start a new session; the UI and scenario replay must make that behavior clear.

Test incremental reuse explicitly: instrument the initialization entry point and require exactly one initialization across a fixed-goal replay, verify the start/key bookkeeping follows the algorithm after movement, and check retained search values on an unaffected part of a controlled fixture. A test must fail if each map event reinitializes the search. Verify that a duplicate event ID does not move the robot, change the map revision, or apply an update a second time. Review the implementation in addition to these tests; route-cost agreement alone does not establish that the algorithm is incremental.

For comparisons, use the same map, start, goal, and map-event sequence. Compare valid route costs with the oracle, not necessarily the exact route geometry: multiple shortest routes may exist.

## Proposed repository layout

```text
AI-TE-303/
  README.md
  CONTRIBUTING.md
  requirements.txt
  requirements-dev.txt
  .gitignore
  app.py
  expert_system/
    __init__.py
    README.md
    main.py
    models.py
    engine.py
    knowledge_base/
      rules.json
  search_algorithm/
    __init__.py
    README.md
    main.py
    grid.py
    models.py
    dstar_lite.py
    astar.py
  data/
    diagnostic_scenarios/
    search_scenarios/
  tests/
    expert_system/
    search_algorithm/
      oracle.py
    integration/
  tools/
    replay_demo.py
    benchmark_search.py
  docs/
    PROJECT_PLAN.md
    MODULE_CONTRACTS.md
    TEAMMATE_TASKS.md
    EXPERT_SYSTEM.md
    SEARCH_ALGORITHM.md
    DEMO_GUIDE.md
    evidence/
  .github/
    workflows/
      tests.yml
```

Create only files needed by completed steps. Empty directories do not need placeholder files merely to inflate the structure. Each module gets its own README describing purpose, input, run command, output, and limitations.

Keep `.venv/`, caches, private `.env` files, Git bundles, and large temporary recordings outside tracked source. Keep the supplied lecture files and existing analysis backups in their current workspace locations. Copy the final English planning/handoff files into the new repository when implementation starts.

## Commit and push plan

A commit records one coherent, reviewable local change. A push transfers commits to the remote branch. For this beginner workflow, push after a tested commit or a short group of related tested commits. There is no target number of commits, and one push can contain several commits.

Suggested checkpoints below are work boundaries, not a requirement to fabricate a fixed history. Include behavior tests with the implementation they verify. A separate test commit is useful for an independent edge-case audit or regression discovered later.

| Checkpoint | Owner | Example English commit message | Observable outcome |
|---|---|---|---|
| Project bootstrap | Lead | `chore: initialize project layout and team documentation` | Scope, dependencies, contracts, ownership, and run instructions are recorded |
| Baseline search | Lead | `feat: add validated grid maps and A-star baseline` | A static map produces a validated route with tests and an independent oracle |
| Initial D* Lite search | Lead | `feat: implement D-star Lite initial planning` | Initial routes match optimal oracle costs |
| Incremental search | Lead | `feat: repair routes after map and start changes` | Blocking, reopening, and moving-start cases reuse search state and pass tests |
| Diagnostic knowledge | Teammate | `feat: add diagnostic rule data and scenario fixtures` | Rule data and scenario inputs load with documented sources and validation |
| Diagnostic inference | Teammate | `feat: implement forward chaining and rule explanations` | Confirmed observations produce an inspectable inference trace |
| Evidence correction | Teammate | `fix: recalculate diagnoses after corrected observations` | Unknown observations remain unknown and obsolete conclusions disappear |
| Diagnostic boundary audit | Teammate | `test: cover incomplete and invalid diagnostic evidence` | Invalid, incomplete, multi-finding, and unsupported cases behave as documented |
| Visual planning demo | Lead | `feat: visualize dynamic routes and planner metrics` | The presenter can move the start, edit obstacles, and view route results |
| Shared demonstration | Both, separate owned changes | `feat: connect diagnostic results to the simulation` | A completed diagnosis can visibly pause simulated movement and show a recommendation |
| Reproduction and explanation | Teammate | `docs: document diagnostic scenarios and limitations` | A teammate-written guide matches actual observed output |
| Final evidence | Both, owned artifacts | `docs: add verified demo evidence and comparison results` | Outputs reference the actual tested source revision and scenario IDs |

A practical PR grouping is bootstrap, baseline search, D* Lite, expert-system increments, visual demo, integration, and evidence. Each PR can contain several meaningful commits. The review scope should be small enough to inspect before merging.

Protect `main` after the initial repository bootstrap: require PRs, passing Python test checks once present, and prevent force pushes/deletion. With two contributors, cross-review feature PRs. Enable normal merge commits so individual feature commits remain visible in main's history. Squash merging combines them into one commit and is not the selected method for this assignment.

After a merge, start the next feature from updated `main`. Do not have both people edit the same knowledge-base or route-planner files simultaneously.

## Running evidence and acceptance

| Scenario | Visible demonstration | Required check |
|---|---|---|
| Initial route | Map, start, goal, and planned route | Every move is valid; route cost equals the independent optimal oracle |
| Robot advances | Start moves along the grid | Search session persists; new route starts at the new position |
| Corridor closes | An obstacle is added to the current route | The next route avoids it and remains optimal on the changed map |
| Corridor reopens | The same obstacle is removed | The planner handles decreased costs and recovers a valid route |
| Goal disconnected and recovered | Access is fully closed and subsequently restored | Clear unreachable status, followed by valid recovery without a crash |
| Supported diagnosis | Confirmed observations are entered | Findings, rule IDs, and reasons correspond to those observations |
| Unknown evidence | One required observation is left unknown | No invented observation or unsupported definitive conclusion appears |
| Corrected observation | A previously supplied fact is changed | Earlier dependent conclusions disappear when no longer justified |
| Invalid evidence | A documented invalid value/combination is supplied | Clear invalid-input result rather than silent coercion |
| Combined demo | Diagnosis recommends pausing a robot | Simulated motion pauses and the explanation remains visible |

Export the actual scenario inputs, result summaries, and test output. Record the tested source commit SHA, scenario IDs, Python/dependency versions, environment, and whether there were uncommitted code changes. Do not type expected timings or successful results into reports before running the program.

Search metrics include route cost, processed/expanded states with a documented definition, queue operations, and algorithm time. Report initial planning separately from each repair and cumulative work. Exclude rendering, animation delays, and installation. Repeat timings, report a median, and include cases where incremental search gives no benefit. Memory measurements are optional and must be measured if reported. Do not promise that D* Lite is always faster than repeated A*.

Evidence package:

1. Live demo with input changes by the presenter.
2. Real screen recording of the named scenarios, kept outside source if large.
3. Exported replay results and benchmark CSV/JSON with source revision metadata.
4. Passing GitHub Actions for the integrated source revision.
5. Fresh clone on the teammate's laptop, followed by setup, tests, and both module demonstrations.
6. A tested release tag such as `v0.1.0-demo`, selected only after integration passes.

Documentation/evidence commits can follow a test run. Their metadata should reference the code revision actually tested; do not manufacture a self-referential commit SHA inside generated evidence.

## Proposed setup and commands

First inspect each member's existing Python and Git installations. Target one mutually available supported Python version, initially Python 3.12 or 3.13, and use the same tested version in CI. Reuse working installations. Use a project virtual environment and pin dependency versions after verifying compatibility.

Required dependencies are Streamlit for the interface and pytest for tests. The core diagnosis and search modules should otherwise use Python's standard library. GitHub CLI is optional for the teammate; Git or GitHub Desktop can perform their collaboration workflow.

The following are intended commands after the repository and program exist. They have not been executed for this project. Run them from the actual cloned repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m expert_system.main --scenario data/diagnostic_scenarios/drive_blockage.json
.\.venv\Scripts\python.exe -m search_algorithm.main --scenario data/search_scenarios/corridor_changes.json
.\.venv\Scripts\python.exe tools/replay_demo.py --output artifacts/demo
.\.venv\Scripts\python.exe -m streamlit run app.py
```

`requirements-dev.txt` should include `requirements.txt` plus pinned test dependencies. Directly invoking the virtual environment's Python avoids a PowerShell activation-policy change. UI access will be local, and the CLI commands provide a fallback if interface rendering is disrupted.

## Two-day schedule and fallback

| Period | Lead | Teammate | Shared completion gate |
|---|---|---|---|
| Friday, October 9 | Repository bootstrap plan, freeze contracts, begin validated map/baseline | Review handoff, draft rule data and named diagnostic cases | Both know ownership and data format; first real increments begin |
| Saturday morning | D* Lite core and dynamic tests | Inference engine and trace tests | Each module can run independently |
| Saturday afternoon/evening | Visual route demo, replay/export, integration adapter | Missing/corrected evidence behavior, diagnostic guide, integration review | Both modules run together before optional extensions |
| Sunday morning, October 11 | Resolve regression failures and verify results | Fresh-clone run, diagnostic demonstration, cross-review | Integrated tests pass; actual evidence is captured |
| Before confirmed Sunday cutoff | Select tested demo version and verified local backup | Rehearse and check submission contents | No unfinished optional feature blocks delivery |

Proposed internal gates: by Saturday evening, both modules must pass their core tests and run one paired scenario through the CLI. If that gate is missed, drop all optional work and finish the headless demonstration before visual polish. By Sunday midday, freeze the required code, reproduce it from a clean clone, and capture the actual evidence. These are team targets, not confirmed submission times; move them earlier if the lecturer's cutoff requires it.

If time becomes tight, remove Bayesian work, elaborate animations, weighted terrain, and extra visual styling first. Preserve the two working modules, D* Lite's incremental behavior, explanations, named scenarios, and running evidence. If D* Lite correctness remains unresolved, do not label a repeated A* implementation as D* Lite: report the limitation and resolve the algorithm before presenting that claim.

Push tested work to the shared repository during development. Before submission, save and verify a Git bundle of committed history outside the checkout. Preserve any uncommitted work separately. A fork is not required by this backup plan.

## Suitability and limits to explain

| Method | Suitable use | Limitation / unsuitable use |
|---|---|---|
| Rule-based diagnosis | A bounded set of observations and explainable domain rules | Novel faults and unsupported evidence need an explicit uncertain result; illustrative rules do not establish real-world accuracy |
| D* Lite | A route to a fixed goal with changing map information and a moving start | More bookkeeping than A*; small static maps may not benefit; this grid model does not solve time-dependent moving-obstacle avoidance |
| Repeated A* | Clear baseline for independently searching each current map | Recomputes its search for each changed snapshot in this comparison |

## Sources

- Supplied expert-system lecture slides, `P02-Expert System-WAC.pptx`, slides 4-8: knowledge base, rules, and inference engine. Original course files are outside this repository.
- Supplied search lecture slides, `P03-Search-WAC.pptx`: search baselines and heuristics.
- Supplied course LMS snapshot, pages 5-6: expert-system and search resource index.
- Supplied classroom photographs: team/repository/branch organization and README expectations.
- Koenig and Likhachev, [D* Lite, AAAI 2002](https://idm-lab.org/bib/abstracts/papers/aaai02b.pdf): primary algorithm reference.
- [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow): branch, commit, push, PR, review, and merge workflow.
- [GitHub merge methods](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github): preserving feature commits with normal merge.
- [Streamlit local setup and run](https://docs.streamlit.io/get-started/installation/command-line) and [session state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state): local UI and persistent session design.

These sources support the methods and workflow. The warehouse application, division of work, schedule, and acceptance criteria are this team's proposed design, not experimental results from those sources.
