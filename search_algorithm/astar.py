"""A* search on the project's finite four-neighbor grid."""

from heapq import heappop, heappush
from itertools import count
from math import inf
from time import perf_counter

from .grid import Grid, GridError
from .models import Position, SearchMetrics, SearchResult


def _manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(grid: Grid, start: object, goal: object) -> SearchResult:
    """Return a shortest unit-cost route or a structured failure result."""
    started = perf_counter()
    metrics = SearchMetrics()

    def finish(
        status: str,
        path: list[Position] | None = None,
        cost: int | None = None,
        message: str = "",
    ) -> SearchResult:
        metrics.elapsed_ms = max(0.0, (perf_counter() - started) * 1000.0)
        return SearchResult(
            status=status, path=path or [], cost=cost, metrics=metrics, message=message
        )

    if not isinstance(grid, Grid):
        return finish("invalid_input", message="grid must be a Grid instance")

    try:
        start_cell = grid.validate_position(start, label="start")
        goal_cell = grid.validate_position(goal, label="goal")
    except GridError as error:
        return finish("invalid_input", message=str(error))

    serial = count()
    frontier: list[tuple[int, int, int, Position]] = []
    heappush(frontier, (_manhattan(start_cell, goal_cell), 0, next(serial), start_cell))
    metrics.queue_pushes += 1
    best_cost: dict[Position, int] = {start_cell: 0}
    predecessor: dict[Position, Position] = {}

    while frontier:
        _, queued_cost, _, current = heappop(frontier)
        metrics.queue_pops += 1
        if queued_cost != best_cost.get(current):
            continue

        metrics.processed_states += 1
        if current == goal_cell:
            path = [goal_cell]
            while path[-1] != start_cell:
                path.append(predecessor[path[-1]])
            path.reverse()
            return finish("found", path=path, cost=queued_cost)

        for neighbor in grid.neighbors(current):
            edge_cost = grid.cost(current, neighbor)
            if edge_cost == inf:
                continue
            candidate_cost = queued_cost + int(edge_cost)
            if candidate_cost >= best_cost.get(neighbor, inf):
                continue

            best_cost[neighbor] = candidate_cost
            predecessor[neighbor] = current
            priority = candidate_cost + _manhattan(neighbor, goal_cell)
            heappush(
                frontier,
                (priority, candidate_cost, next(serial), neighbor),
            )
            metrics.queue_pushes += 1

    return finish(
        "unreachable",
        message="No route connects the start and goal on the current map.",
    )
