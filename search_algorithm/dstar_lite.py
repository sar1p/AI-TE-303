"""D* Lite, using the basic Koenig--Likhachev (AAAI 2002) formulation.

Search runs backward from a fixed goal. The queue uses lazy invalidation;
obsolete keys after start movement are distinct from invalidated heap entries.
"""

import heapq
import math
from itertools import count
from time import perf_counter

from .grid import Grid, GridError
from .models import Position, SearchMetrics, SearchResult

Key = tuple[float, float]


def manhattan(first: Position, second: Position) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


class DStarLitePlanner:
    """Persistent shortest-path state for one finite grid and fixed goal."""

    def __init__(self, grid: Grid, start: Position, goal: Position):
        self.grid = grid.clone()
        self.start = self.grid.validate_position(start, "start")
        self.goal = self.grid.validate_position(goal, "goal")
        self.k_m = 0
        self._last_start = self.start
        self.initialization_count = 0
        self._metrics = SearchMetrics()
        self._initialize()

    def _initialize(self) -> None:
        self.initialization_count += 1
        cells = [(r, c) for r in range(self.grid.height) for c in range(self.grid.width)]
        self.g = dict.fromkeys(cells, math.inf)
        self.rhs = dict.fromkeys(cells, math.inf)
        self.rhs[self.goal] = 0
        self._queue: list[tuple[float, float, int, Position]] = []
        self._active: dict[Position, tuple[Key, int]] = {}
        self._sequence = count()
        self._push(self.goal, self._key(self.goal))

    def _key(self, cell: Position) -> Key:
        lower = min(self.g[cell], self.rhs[cell])
        return lower + manhattan(self.start, cell) + self.k_m, lower

    def _push(self, cell: Position, key: Key) -> None:
        generation = next(self._sequence)
        self._active[cell] = (key, generation)
        heapq.heappush(self._queue, (*key, generation, cell))
        self._metrics.queue_pushes += 1

    def _discard_stale_entries(self) -> None:
        while self._queue:
            first, second, generation, cell = self._queue[0]
            if self._active.get(cell) == ((first, second), generation):
                return
            heapq.heappop(self._queue)
            self._metrics.queue_pops += 1

    def _top_key(self) -> Key:
        self._discard_stale_entries()
        if not self._queue:
            return math.inf, math.inf
        return self._queue[0][0], self._queue[0][1]

    def _pop(self) -> tuple[Position, Key]:
        self._discard_stale_entries()
        first, second, _, cell = heapq.heappop(self._queue)
        del self._active[cell]
        self._metrics.queue_pops += 1
        return cell, (first, second)

    def _update_vertex(self, cell: Position) -> None:
        if cell != self.goal:
            self.rhs[cell] = min(
                (self.grid.cost(cell, neighbor) + self.g[neighbor]
                 for neighbor in self.grid.neighbors(cell)),
                default=math.inf,
            )
        self._active.pop(cell, None)
        if self.g[cell] != self.rhs[cell]:
            self._push(cell, self._key(cell))

    def _compute_shortest_path(self) -> None:
        while self._top_key() < self._key(self.start) or self.rhs[self.start] != self.g[self.start]:
            if not self._queue:
                raise RuntimeError("An inconsistent start has no queued repair state.")
            cell, old_key = self._pop()
            new_key = self._key(cell)
            if old_key < new_key:
                self._push(cell, new_key)
            elif self.g[cell] > self.rhs[cell]:
                self.g[cell] = self.rhs[cell]
                self._metrics.processed_states += 1
                for predecessor in self.grid.neighbors(cell):
                    self._update_vertex(predecessor)
            else:
                self.g[cell] = math.inf
                self._metrics.processed_states += 1
                self._update_vertex(cell)
                for predecessor in self.grid.neighbors(cell):
                    self._update_vertex(predecessor)

    def plan(self) -> SearchResult:
        """Repair inconsistent values, then extract a deterministic optimal route."""
        started = perf_counter()
        self._compute_shortest_path()
        path: list[Position] = []
        if math.isfinite(self.g[self.start]):
            path = [self.start]
            while path[-1] != self.goal:
                current = path[-1]
                choices = [
                    (self.grid.cost(current, cell) + self.g[cell], cell)
                    for cell in self.grid.neighbors(current)
                ]
                value, following = min(choices, default=(math.inf, current))
                if not math.isfinite(value) or following in path:
                    raise RuntimeError("Repaired values do not define a finite acyclic route.")
                path.append(following)
        self._metrics.elapsed_ms = (perf_counter() - started) * 1000
        result = SearchResult(
            status="found" if path else "unreachable",
            path=path,
            cost=len(path) - 1 if path else None,
            metrics=self._metrics,
            message="" if path else "No route connects the current robot and goal.",
        )
        self._metrics = SearchMetrics()
        return result
