# Contributing

Use English for source code, comments, interface text, documentation, branch
names, commits, pull requests, and workflow names.

The lead owns search, the visual application, shared contracts, and CI. The
teammate owns the expert system and its tests. See
[TEAMMATE_TASKS.md](docs/TEAMMATE_TASKS.md) before beginning diagnostic work.

## Daily workflow

1. Update your local `main`: `git switch main` then `git pull --ff-only`.
2. Create one branch per coherent feature, such as `feature/expert-rules`.
3. Make a working change and run the relevant tests.
4. Stage only the files you intend to change. Use `git diff --staged` to inspect them.
5. Commit one complete change, for example `feat: add forward-chaining inference`.
6. Push your branch: `git push -u origin feature/expert-rules`.
7. Open a pull request, describe the behavior and actual checks, and ask the other
   member to review it. Fix feedback on the same branch.
8. Merge with a merge commit after required checks pass. This preserves each
   contributor's commits. Update local `main` before starting the next feature.

A **commit** records a local version. A **push** uploads one or several commits.
A **branch** isolates work. A **pull request** makes the change reviewable.
A **merge commit** connects the feature history to `main`. Avoid arbitrary tiny
commits, invented authors, force pushes, and rewriting shared history.

Use collaborator access for this two-person project. A fork is useful when you
cannot push branches to the original repository; it is optional here. A fork is
not a replacement for an offline backup. The lead maintains a verified Git
bundle outside this checkout.

## Validation

Use Python 3.12 and the project virtual environment. Install
`requirements-dev.txt`, then run `python -m pytest -q`. Core search also runs with
the Python standard library. Tests must exercise behavior rather than copy the
algorithm under test. Changes to shared contracts need both members' agreement.

Keep credentials, virtual environments, generated temporary exports, lecture
documents, and personal files out of Git. A diagnosis demonstration requires
real inference from documented facts; screenshots and benchmark values must
come from actual runs.
