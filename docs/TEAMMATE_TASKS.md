# AI-TE-303 Teammate Handoff

Status: work reserved for the second team member. Repository setup has begun; the diagnostic engine remains pending. Use [MODULE_CONTRACTS.md](MODULE_CONTRACTS.md) for the frozen dictionary interface. Working delivery target: Sunday, October 11, 2026; exact submission time is unconfirmed.

## Your responsibility

Build the warehouse robot expert-system module. Your work includes code, knowledge-base data, meaningful tests, examples, and an explanation of the diagnosis process for the presentation.

The lead builds D* Lite route planning, the visual application, and the integration adapter. Agree on the module contract before implementation so both people can work independently.

All repository content uses English. Work on your own feature branch and use your own Git/GitHub identity for your actual contributions.

## Prerequisites

- A GitHub account and accepted collaborator access to the shared `AI-TE-303` repository.
- Python 3.12, matching the lead's tested environment and CI.
- Git or GitHub Desktop. GitHub CLI is optional.
- A local clone in its own folder, an editor or coding assistant, and a project virtual environment.
- The repository's project plan, module contracts, pinned dependency files, and this handoff.
- A short shared agreement on which observations mean known true, known false, or unknown.

Authenticate normally through your chosen GitHub tool.

## Owned files

```text
expert_system/
tests/expert_system/
data/diagnostic_scenarios/
docs/EXPERT_SYSTEM.md
```

Coordinate shared contract changes with the lead. Do not independently redesign `search_algorithm/`, `app.py`, dependency files, CI, or repository settings. Review those components through the agreed collaboration workflow when useful.

## Frozen diagnosis contract

`expert_system.engine.diagnose(facts: dict[str, object]) -> dict`.
The exact JSON-compatible fields and record shapes are defined in [MODULE_CONTRACTS.md](MODULE_CONTRACTS.md).

The agreed result has:

- `status`: `ok`, `insufficient_evidence`, or `invalid_input`.
- `findings`: supported suspected conditions with contributing rule IDs.
- `rule_trace`: ordered rule firings with the premises used, derived facts, and reasons.
- `recommendations`: English advice and agreed action IDs where applicable.
- `missing_facts`: relevant observations that were not supplied or are unknown.

Treat an absent observation or `None` as unknown. Never interpret it as a negative observation. Start each diagnosis from the supplied raw observations, do not mutate the input, and keep derived facts inside that inference session.

The application handles corrected observations by replacing the raw value and invoking a fresh diagnosis. Your engine must not retain an earlier conclusion that is no longer supported.

Several findings may coexist. Validate contradictory representations of the same observation and unsupported data types; document exactly what is invalid. Do not force all unusual combinations into a single fault or silently invent evidence.

Recommendations may use agreed action IDs such as `pause_robot`, `check_power`, `check_drive`, and `check_encoder`. The engine must not depend on Streamlit or import route-planner code.

## Work increments

| Increment | Deliverable | Acceptance |
|---|---|---|
| Rule data | `rules.json`, rule loader, and named scenario inputs | Rules have unique IDs, declared conditions/conclusions, English reasons, and provenance/validation labels; malformed data is rejected |
| Inference | Forward chaining until no supported new facts remain | A multi-rule chain works; firing is deterministic; repeated conditions do not cause an infinite loop |
| Explanation | Structured rule trace and supported findings | Every returned finding has a trace grounded in the supplied or derived facts |
| Missing and corrected evidence | Unknown handling and fresh inference | Unknown data does not fire a rule as false/true; correcting a premise removes dependent obsolete findings |
| Boundary tests | Tests for invalid and incomplete data, unsupported findings, and simultaneous findings | The documented result status and findings match explicit expected cases |
| Standalone demo | `main.py`, module README, and expert-system guide | The module runs from the repo root without requiring the visual application |

Initial target scope is four suspected conditions, around eight observation types, and 8-12 meaningful rules. This is a proposed size, not a lecturer requirement. Start with low battery, drive blockage, motor connection problems, and encoder signal problems. Check the diagnostic logic rather than adding rules only to reach a count.

Knowledge records must distinguish sourced rules from illustrative simulation rules. Do not claim measured diagnostic accuracy or add probability percentages without a justified model and evidence.

Bayesian inference is optional. Discuss it only after the required engine, explanations, cases, and integrated demo are working.

## Scenario checklist

1. Confirmed observations support a suspected condition, and the trace explains why.
2. A conclusion derived by one rule enables another rule.
3. Missing observations produce relevant missing-evidence information.
4. A corrected observation removes the previous dependent diagnosis on the next call.
5. Known negative observations do not behave like missing observations.
6. Invalid values or a documented contradictory representation return `invalid_input`.
7. Facts outside the supported rule set do not produce an invented definitive finding.
8. Compatible simultaneous findings are retained without assuming a single fault.
9. Repeating a diagnosis with the same input produces the same findings and trace.
10. Rule cycles or repeated conclusions terminate without an infinite loop.

Use hand-written expected outcomes derived from the rule definitions, not the engine's own outputs as its only test oracle. The final count of passing tests comes from an actual run.

## Commit, push, and review

Suggested messages for real completed increments:

```text
feat: add diagnostic rules and scenario fixtures
feat: implement forward chaining and rule explanations
fix: recalculate diagnoses after corrected observations
test: cover incomplete and invalid diagnostic evidence
docs: document diagnostic scenarios and limitations
```

Include relevant behavior tests with each implementation increment. Push tested commits to your feature branch. Open a draft PR early if you need review, then mark it ready when its stated acceptance checks pass. One feature PR may contain several commits.

Use a normal merge commit when the lead merges reviewed work so your original feature commits remain in the shared history. Update from `main` before starting another feature. Each member reviews the other module's assumptions and recorded demo behavior.

The following commands are examples for use after the repository and files exist. They have not been run for this project. Use the actual clone URL supplied by the lead, and run from your actual repository root.

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/expert-system
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests/expert_system -q
git status
git diff
git add expert_system tests/expert_system data/diagnostic_scenarios docs/EXPERT_SYSTEM.md
git diff --cached
git commit -m "feat: implement forward chaining and rule explanations"
git push -u origin feature/expert-system
```

Use `git switch -c` only when creating a new branch; use `git switch feature/expert-system` to revisit one that exists. Stage only paths that exist and belong to the increment being committed. Later pushes can use `git push` once the branch has an upstream.

## Evidence and presentation

On Sunday, reproduce the project from a fresh clone on your own laptop. Capture the actual Python/dependency versions, source commit SHA, test results, and named scenario output. Run both modules and the visual application using the documented commands.

For your presentation, explain:

- Why a knowledge base and rule engine are appropriate for the bounded diagnosis problem.
- What facts the system takes and how unknown values differ from known negatives.
- One chain of fired rules and its English explanation.
- What changes when an observation is corrected.
- Which rule sources are established and which are illustrative.
- Where the system can fail: missing rules, inaccurate observations, unsupported faults, or an unvalidated knowledge base.

A real screen recording and exported outputs complement the live demo. An interface screenshot alone does not establish that the algorithms executed correctly.

## Portable prompt for your coding assistant

Copy this prompt into your own coding assistant after opening the real local clone. The assistant should inspect the actual repository before assuming any file exists.

> Work on my assigned expert-system module in the AI-TE-303 group repository. First read the project plan, module contracts, and teammate tasks. Confirm the active feature branch and current files. Implement one reviewable increment at a time within expert_system/, tests/expert_system/, data/diagnostic_scenarios/, and docs/EXPERT_SYSTEM.md. Use English throughout. The module performs deterministic forward chaining from raw observations and returns structured findings, rule explanations, recommendations, and missing facts. Treat missing/None evidence as unknown. Recompute from raw facts after corrections, and do not retain unsupported conclusions. Validate input and rule data. Mark illustrative domain rules as illustrative. Keep the module independent of the UI and route planner. Add meaningful behavioral tests and run them; report commands and actual results. Do not invent benchmark or diagnosis results. Coordinate shared interface changes before editing other components. Show the staged diff before committing a completed increment, use my configured Git identity, and push to my feature branch when authorized. Leave merging to the group review workflow. Reserve Bayesian reasoning until the required module passes.

## Delivery checklist

- [ ] Contracts agreed with the lead.
- [ ] Rule data, sources, and input types documented.
- [ ] Inference, explanations, and correction behavior implemented.
- [ ] Meaningful module tests pass.
- [ ] Standalone scenario demo runs.
- [ ] Changes committed and pushed through the teammate's account.
- [ ] PR review and shared integration completed.
- [ ] Fresh-clone reproduction and actual evidence captured.
- [ ] Presentation and limitations rehearsed.

No item is marked complete before the corresponding work and verification occur.
