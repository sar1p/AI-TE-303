"""Independent uniform-cost oracle for finite four-neighbor grids."""

from heapq import heappop, heappush


def ucs_cost(grid, start, goal):
    """Return the optimal unit-cost path length, or None when unreachable.

    The oracle reads only the grid dimensions and blocked-cell set. It does not
    use the production grid's neighbor, edge-cost, or heuristic helpers.
    Endpoints are expected to have been validated by the caller.
    """
    height = grid.height
    width = grid.width
    blocked = set(grid.blocked)
    if start in blocked or goal in blocked:
        return None

    distances = {start: 0}
    frontier = [(0, start)]
    while frontier:
        distance, cell = heappop(frontier)
        if distance != distances.get(cell):
            continue
        if cell == goal:
            return distance

        row, column = cell
        for neighbor in (
            (row - 1, column),
            (row + 1, column),
            (row, column - 1),
            (row, column + 1),
        ):
            next_row, next_column = neighbor
            if not (0 <= next_row < height and 0 <= next_column < width):
                continue
            if neighbor in blocked:
                continue
            candidate = distance + 1
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                heappush(frontier, (candidate, neighbor))
    return None
