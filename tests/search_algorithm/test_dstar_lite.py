"""D* Lite contract tests against an independent UCS cost oracle."""

import random

import pytest

from search_algorithm.dstar_lite import DStarLitePlanner
from search_algorithm.grid import Grid, GridError
from tests.search_algorithm.oracle import ucs_cost


def _coordinates(path):
    return [tuple(cell) for cell in path]


def _assert_matches_oracle(grid, result, start, goal):
    expected_cost = ucs_cost(grid, start, goal)
    if expected_cost is None:
        assert result.status == "unreachable"
        assert result.path == []
        assert result.cost is None
        return

    path = _coordinates(result.path)
    assert result.status == "found"
    assert result.cost == expected_cost
    assert path[0] == start
    assert path[-1] == goal
    assert len(path) - 1 == result.cost
    blocked = set(grid.blocked)
    for row, column in path:
        assert 0 <= row < grid.height
        assert 0 <= column < grid.width
        assert (row, column) not in blocked
    for first, second in zip(path, path[1:]):
        assert abs(first[0] - second[0]) + abs(first[1] - second[1]) == 1


def _state_snapshot(planner):
    return (
        set(planner.grid.blocked),
        planner.grid.revision,
        planner.start,
        planner.goal,
        planner.k_m,
        dict(planner.g),
        dict(planner.rhs),
    )


def test_basic_initial_path_matches_ucs_and_planner_owns_grid_copy():
    source = Grid(4, 5, blocked={(1, 1), (1, 2), (2, 3)})
    start = (0, 0)
    goal = (3, 4)
    planner = DStarLitePlanner(source, start, goal)

    assert planner.grid is not source
    assert planner.grid.blocked == source.blocked
    result = planner.plan()
    _assert_matches_oracle(planner.grid, result, start, goal)
    assert planner.initialization_count == 1


def test_valid_start_equal_to_goal_has_zero_cost():
    grid = Grid(3, 3, blocked={(0, 1)})
    planner = DStarLitePlanner(grid, (1, 1), (1, 1))

    result = planner.plan()

    assert result.status == "found"
    assert _coordinates(result.path) == [(1, 1)]
    assert result.cost == 0
    _assert_matches_oracle(planner.grid, result, planner.start, planner.goal)


def test_invalid_start_or_goal_is_rejected():
    grid = Grid(3, 4, blocked={(1, 1)})
    invalid_cases = (
        ((-1, 0), (2, 3)),
        ((0, 0), (3, 3)),
        ((1, 1), (2, 3)),
        ((0, 0), (1, 1)),
    )
    for start, goal in invalid_cases:
        with pytest.raises(GridError):
            DStarLitePlanner(grid, start, goal)


def test_unreachable_goal_becomes_reachable_after_restoring_corridor():
    grid = Grid(3, 5, blocked={(0, 2), (1, 2), (2, 2)})
    planner = DStarLitePlanner(grid, (1, 0), (1, 4))

    first = planner.plan()
    _assert_matches_oracle(planner.grid, first, planner.start, planner.goal)
    assert first.status == "unreachable"

    planner.update_cells([{"cell": [1, 2], "blocked": False}])
    restored = planner.plan()
    _assert_matches_oracle(planner.grid, restored, planner.start, planner.goal)
    assert restored.status == "found"
    assert planner.initialization_count == 1


def test_blocking_and_reopening_route_cell_match_ucs():
    grid = Grid(3, 5)
    planner = DStarLitePlanner(grid, (1, 0), (1, 4))
    first = planner.plan()
    _assert_matches_oracle(planner.grid, first, planner.start, planner.goal)

    planner.update_cells([{"cell": [1, 2], "blocked": True}])
    blocked = planner.plan()
    _assert_matches_oracle(planner.grid, blocked, planner.start, planner.goal)
    assert (1, 2) not in _coordinates(blocked.path)

    planner.update_cells([{"cell": [1, 2], "blocked": False}])
    reopened = planner.plan()
    _assert_matches_oracle(planner.grid, reopened, planner.start, planner.goal)
    assert reopened.cost == first.cost
    assert planner.initialization_count == 1


def test_legal_start_move_updates_manhattan_km_without_resetting_state():
    planner = DStarLitePlanner(Grid(1, 5), (0, 0), (0, 4))
    initial = planner.plan()
    _assert_matches_oracle(planner.grid, initial, planner.start, planner.goal)
    g_table = planner.g
    rhs_table = planner.rhs
    retained_g = planner.g[(0, 2)]
    retained_rhs = planner.rhs[(0, 2)]

    planner.move_start((0, 1))
    result = planner.plan()

    assert planner.start == (0, 1)
    assert planner.goal == (0, 4)
    assert planner.k_m == 1
    assert planner.g is g_table
    assert planner.rhs is rhs_table
    assert planner.g[(0, 2)] == retained_g == 2
    assert planner.rhs[(0, 2)] == retained_rhs == 2
    assert planner.initialization_count == 1
    _assert_matches_oracle(planner.grid, result, planner.start, planner.goal)


def test_replay_keeps_one_initialization_across_start_and_map_events():
    planner = DStarLitePlanner(Grid(3, 6), (1, 0), (1, 5))
    g_table = planner.g
    rhs_table = planner.rhs
    result = planner.plan()
    _assert_matches_oracle(planner.grid, result, planner.start, planner.goal)

    planner.move_start((1, 1))
    result = planner.plan()
    _assert_matches_oracle(planner.grid, result, planner.start, planner.goal)
    assert planner.initialization_count == 1

    planner.update_cells([{"cell": [1, 3], "blocked": True}])
    result = planner.plan()
    _assert_matches_oracle(planner.grid, result, planner.start, planner.goal)
    assert planner.g is g_table
    assert planner.rhs is rhs_table
    assert planner.initialization_count == 1

    planner.update_cells([{"cell": [1, 3], "blocked": False}])
    result = planner.plan()
    _assert_matches_oracle(planner.grid, result, planner.start, planner.goal)
    assert planner.initialization_count == 1


def test_invalid_update_batches_are_atomic():
    planner = DStarLitePlanner(Grid(1, 5), (0, 0), (0, 4))
    planner.plan()
    invalid_batches = (
        # A valid first item must not partially apply before the invalid goal.
        [{"cell": [0, 1], "blocked": True}, {"cell": [0, 4], "blocked": True}],
        [{"cell": [0, 0], "blocked": True}],
        [{"cell": [0, 2], "blocked": True}, {"cell": [0, 2], "blocked": False}],
        [{"cell": [1, 2], "blocked": True}],
        [{"cell": [True, 2], "blocked": True}],
        [{"cell": [0, 2], "blocked": 1}],
        [{"cell": [0, 2], "blocked": True, "unexpected": "value"}],
    )

    for batch in invalid_batches:
        before = _state_snapshot(planner)
        g_table = planner.g
        rhs_table = planner.rhs
        with pytest.raises(GridError):
            planner.update_cells(batch)
        assert _state_snapshot(planner) == before
        assert planner.g is g_table
        assert planner.rhs is rhs_table


def test_nonadjacent_start_move_is_rejected_without_state_change():
    planner = DStarLitePlanner(Grid(2, 5), (0, 0), (0, 4))
    planner.plan()
    before = _state_snapshot(planner)

    with pytest.raises(GridError):
        planner.move_start((0, 2))

    assert _state_snapshot(planner) == before
    assert planner.initialization_count == 1


def test_fixed_seed_dynamic_maps_match_independent_ucs_oracle():
    rng = random.Random(303)
    for _map_index in range(60):
        height = rng.randint(4, 6)
        width = rng.randint(4, 6)
        start = (0, 0)
        goal = (height - 1, width - 1)
        blocked = {
            (row, column)
            for row in range(height)
            for column in range(width)
            if (row, column) not in (start, goal) and rng.random() < 0.28
        }
        planner = DStarLitePlanner(Grid(height, width, blocked=blocked), start, goal)
        result = planner.plan()
        _assert_matches_oracle(planner.grid, result, planner.start, planner.goal)
        assert planner.initialization_count == 1

        for _event_index in range(12):
            candidates = [
                (row, column)
                for row in range(height)
                for column in range(width)
                if (row, column) not in (planner.start, planner.goal)
            ]
            cell = rng.choice(candidates)
            planner.update_cells([{"cell": list(cell), "blocked": cell not in planner.grid.blocked}])
            result = planner.plan()
            _assert_matches_oracle(planner.grid, result, planner.start, planner.goal)
            assert planner.initialization_count == 1

            if result.status == "found" and len(result.path) > 1 and rng.random() < 0.6:
                planner.move_start(tuple(result.path[1]))
                result = planner.plan()
                _assert_matches_oracle(planner.grid, result, planner.start, planner.goal)
                assert planner.initialization_count == 1
