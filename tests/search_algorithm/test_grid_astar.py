import math

import pytest

from search_algorithm.astar import astar
from search_algorithm.grid import Grid, GridError


@pytest.mark.parametrize(
    "height,width",
    [(0, 2), (-1, 2), (2, 0), (2, -1), (True, 2), (2, False)],
)
def test_grid_requires_positive_non_boolean_integer_dimensions(height, width):
    with pytest.raises(GridError):
        Grid(height, width)


def test_rows_round_trip_and_clone_preserve_revision_independently():
    grid = Grid.from_rows([".#.", "...", "##."])
    assert grid.height == 3
    assert grid.width == 3
    assert grid.blocked == {(0, 1), (2, 0), (2, 1)}
    assert grid.to_rows() == [".#.", "...", "##."]

    changed = grid.apply_changes([{"cell": [1, 1], "blocked": True}])
    assert changed == {(1, 1)}
    assert grid.revision == 1

    clone = grid.clone()
    assert clone.to_rows() == grid.to_rows()
    assert clone.revision == grid.revision
    clone.apply_changes([{"cell": (1, 1), "blocked": False}])
    assert clone.revision == 2
    assert (1, 1) not in clone.blocked
    assert (1, 1) in grid.blocked
    assert grid.revision == 1


@pytest.mark.parametrize(
    "rows",
    [[], [""], ["..", "."], [".x"], [".", 3]],
)
def test_from_rows_rejects_empty_ragged_or_invalid_rows(rows):
    with pytest.raises(GridError):
        Grid.from_rows(rows)


@pytest.mark.parametrize(
    "position",
    [(), (1,), (0, 1, 2), (True, 0), (0, False), (1.0, 0), "00"],
)
def test_position_validation_rejects_wrong_shape_and_non_integer_coordinates(position):
    grid = Grid(2, 2)
    with pytest.raises(GridError):
        grid.validate_position(position)


def test_position_validation_checks_bounds_and_blocked_cells():
    grid = Grid(2, 2, blocked=[(0, 1)])
    with pytest.raises(GridError, match="outside"):
        grid.validate_position((-1, 0), label="start")
    with pytest.raises(GridError, match="blocked"):
        grid.validate_position((0, 1), label="goal")
    assert grid.validate_position([0, 1], require_open=False) == (0, 1)
    assert grid.contains((1, 1))
    assert not grid.contains((2, 1))
    assert not grid.contains((True, 1))


def test_neighbors_are_deterministic_and_include_blocked_cells():
    grid = Grid(3, 3, blocked=[(0, 1)])
    assert grid.neighbors((1, 1)) == [(0, 1), (1, 0), (1, 2), (2, 1)]


def test_cost_is_unit_only_for_adjacent_open_cells():
    grid = Grid(2, 3, blocked=[(0, 1)])
    assert grid.cost((0, 0), (1, 0)) == 1
    assert math.isinf(grid.cost((0, 0), (0, 1)))
    assert math.isinf(grid.cost((0, 0), (0, 2)))
    assert math.isinf(grid.cost((0, 0), (2, 0)))
    assert math.isinf(grid.cost((0, 0), (0, 0)))
    assert math.isinf(grid.cost((0, 0), (True, 1)))


@pytest.mark.parametrize(
    "changes,protected",
    [
        ([{"cell": (0, 0), "blocked": True, "extra": 1}], ()),
        ([{"cell": (0, 0)}], ()),
        ([{"cell": (0, 0), "blocked": 1}], ()),
        ([{"cell": (3, 0), "blocked": True}], ()),
        (
            [
                {"cell": (0, 0), "blocked": True},
                {"cell": (1, 1), "blocked": "yes"},
            ],
            (),
        ),
        (
            [
                {"cell": (0, 0), "blocked": True},
                {"cell": (0, 0), "blocked": False},
            ],
            (),
        ),
        ([{"cell": (0, 0), "blocked": True}], ((0, 0),)),
    ],
)
def test_invalid_change_batches_are_atomic(changes, protected):
    grid = Grid(3, 3, blocked=[(2, 2)])
    before = grid.blocked.copy()

    with pytest.raises(GridError):
        grid.apply_changes(changes, protected=protected)

    assert grid.blocked == before
    assert grid.revision == 0


def test_identical_duplicate_updates_apply_once_and_revision_tracks_real_changes():
    grid = Grid(3, 3)
    changed = grid.apply_changes(
        [
            {"cell": [1, 1], "blocked": True},
            {"cell": (1, 1), "blocked": True},
        ]
    )
    assert changed == {(1, 1)}
    assert grid.revision == 1

    assert grid.apply_changes([{"cell": (1, 1), "blocked": True}]) == set()
    assert grid.apply_changes([]) == set()
    assert grid.revision == 1

    assert grid.apply_changes([{"cell": (1, 1), "blocked": False}]) == {(1, 1)}
    assert grid.revision == 2


def test_apply_changes_can_unblock_a_protected_cell_but_not_leave_it_blocked():
    grid = Grid(2, 2, blocked=[(0, 0)])
    assert grid.apply_changes(
        [{"cell": (0, 0), "blocked": False}], protected=[(0, 0)]
    ) == {(0, 0)}
    assert (0, 0) not in grid.blocked
    assert grid.revision == 1


def _assert_valid_route(grid, result, start, goal):
    assert result.status == "found"
    assert result.path[0] == start
    assert result.path[-1] == goal
    assert result.cost == len(result.path) - 1
    for first, second in zip(result.path, result.path[1:]):
        assert grid.cost(first, second) == 1


def test_astar_finds_shortest_valid_path_around_blocked_cells():
    grid = Grid.from_rows([".....", ".###.", "...#.", "##..."])
    result = astar(grid, (0, 0), (3, 4))

    _assert_valid_route(grid, result, (0, 0), (3, 4))
    assert result.cost == 7
    assert result.metrics.processed_states > 0
    assert result.metrics.queue_pops >= result.metrics.processed_states
    assert result.metrics.queue_pushes >= 1
    assert math.isfinite(result.metrics.elapsed_ms)


def test_astar_uses_deterministic_neighbor_order_for_equal_routes():
    result = astar(Grid(2, 2), (0, 0), (1, 1))
    assert result.path == [(0, 0), (0, 1), (1, 1)]
    assert result.cost == 2


def test_astar_start_equal_goal_returns_one_cell_route_and_counts_goal():
    result = astar(Grid(2, 2), (1, 1), (1, 1))
    assert result.status == "found"
    assert result.path == [(1, 1)]
    assert result.cost == 0
    assert result.metrics.processed_states == 1
    assert result.metrics.queue_pops == 1
    assert result.metrics.queue_pushes == 1


def test_astar_reports_unreachable_open_goal():
    grid = Grid.from_rows([".#.", "###", ".#."])
    result = astar(grid, (0, 0), (2, 2))
    assert result.status == "unreachable"
    assert result.path == []
    assert result.cost is None
    assert math.isfinite(result.metrics.elapsed_ms)


@pytest.mark.parametrize(
    "start,goal",
    [
        ((-1, 0), (1, 1)),
        ((0, 0), (2, 2)),
        ((True, 0), (1, 1)),
        ((0, 0), (0, 1)),
    ],
)
def test_astar_returns_invalid_input_for_bad_or_blocked_endpoints(start, goal):
    grid = Grid(2, 2, blocked=[(0, 1)])
    result = astar(grid, start, goal)
    assert result.status == "invalid_input"
    assert result.path == []
    assert result.cost is None
    assert math.isfinite(result.metrics.elapsed_ms)


def test_astar_rejects_non_grid_input_as_invalid():
    result = astar(None, (0, 0), (0, 0))
    assert result.status == "invalid_input"
    assert result.path == []
    assert result.cost is None
