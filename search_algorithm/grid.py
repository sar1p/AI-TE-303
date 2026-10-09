"""Finite four-neighbor grid and validated map updates."""

from collections.abc import Iterable
from math import inf

from .models import Position


class GridError(ValueError):
    """Raised when a grid, position, or map update is invalid."""


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class Grid:
    """A finite, unit-cost, four-neighbor grid."""

    _DIRECTIONS = ((-1, 0), (0, -1), (0, 1), (1, 0))

    def __init__(
        self,
        height: int,
        width: int,
        blocked: Iterable[Position] = (),
    ) -> None:
        if not _is_integer(height) or height <= 0:
            raise GridError("height must be a positive integer")
        if not _is_integer(width) or width <= 0:
            raise GridError("width must be a positive integer")

        self._height = height
        self._width = width
        self.blocked: set[Position] = set()
        self._revision = 0

        try:
            blocked_cells = iter(blocked)
        except TypeError as error:
            raise GridError("blocked must be an iterable of cells") from error

        for index, cell in enumerate(blocked_cells):
            self.blocked.add(
                self.validate_position(
                    cell, label=f"blocked[{index}]", require_open=False
                )
            )

    @property
    def height(self) -> int:
        return self._height

    @property
    def width(self) -> int:
        return self._width

    @property
    def revision(self) -> int:
        return self._revision

    @classmethod
    def from_rows(cls, rows: list[str]) -> "Grid":
        """Build a grid from equal-width strings containing only ``.`` and ``#``."""
        if not isinstance(rows, list) or not rows:
            raise GridError("rows must be a nonempty list of strings")
        if any(not isinstance(row, str) for row in rows):
            raise GridError("every grid row must be a string")

        width = len(rows[0])
        if width == 0:
            raise GridError("grid rows must have positive width")
        if any(len(row) != width for row in rows):
            raise GridError("grid rows must all have the same width")
        if any(character not in ".#" for row in rows for character in row):
            raise GridError("grid rows may contain only '.' and '#'")

        blocked = (
            (row_index, column_index)
            for row_index, row in enumerate(rows)
            for column_index, character in enumerate(row)
            if character == "#"
        )
        return cls(len(rows), width, blocked)

    def to_rows(self) -> list[str]:
        """Return the current map as rows of ``.`` and ``#``."""
        return [
            "".join("#" if (row, column) in self.blocked else "."
                   for column in range(self.width))
            for row in range(self.height)
        ]

    def clone(self) -> "Grid":
        """Return an independent copy, including the current revision number."""
        cloned = Grid(self.height, self.width, self.blocked)
        cloned._revision = self.revision
        return cloned

    @staticmethod
    def _normalize_position(value: object, label: str) -> Position:
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise GridError(f"{label} must contain exactly two integer coordinates")
        row, column = value
        if not _is_integer(row) or not _is_integer(column):
            raise GridError(f"{label} coordinates must be integers, not booleans")
        return (row, column)

    def contains(self, position: object) -> bool:
        """Return whether a coordinate is well-formed and inside the grid."""
        try:
            row, column = self._normalize_position(position, "position")
        except GridError:
            return False
        return 0 <= row < self.height and 0 <= column < self.width

    def validate_position(
        self,
        value: object,
        label: str = "position",
        require_open: bool = True,
    ) -> Position:
        """Normalize and validate one in-bounds position."""
        position = self._normalize_position(value, label)
        row, column = position
        if not (0 <= row < self.height and 0 <= column < self.width):
            raise GridError(f"{label} {position} is outside the grid")
        if require_open and position in self.blocked:
            raise GridError(f"{label} {position} is blocked")
        return position

    def neighbors(self, cell: object) -> list[Position]:
        """Return in-bounds cardinal neighbors, including blocked cells."""
        row, column = self.validate_position(
            cell, label="cell", require_open=False
        )
        result = []
        for row_delta, column_delta in self._DIRECTIONS:
            neighbor = (row + row_delta, column + column_delta)
            if self.contains(neighbor):
                result.append(neighbor)
        return result

    def cost(self, a: object, b: object) -> int | float:
        """Return unit cost for an open adjacent edge, otherwise infinity."""
        try:
            first = self.validate_position(a, label="a", require_open=False)
            second = self.validate_position(b, label="b", require_open=False)
        except GridError:
            return inf

        if first in self.blocked or second in self.blocked:
            return inf
        if abs(first[0] - second[0]) + abs(first[1] - second[1]) != 1:
            return inf
        return 1

    def apply_changes(
        self,
        changes: Iterable[dict],
        protected: Iterable[Position] = (),
    ) -> set[Position]:
        """Apply a validated batch atomically and increment revision once."""
        try:
            protected_values = iter(protected)
        except TypeError as error:
            raise GridError("protected must be an iterable of cells") from error

        protected_cells: set[Position] = set()
        for index, value in enumerate(protected_values):
            protected_cells.add(
                self.validate_position(
                    value, label=f"protected[{index}]", require_open=False
                )
            )

        try:
            change_values = iter(changes)
        except TypeError as error:
            raise GridError("changes must be an iterable of records") from error

        missing = object()
        updates: dict[Position, bool] = {}
        for index, record in enumerate(change_values):
            if not isinstance(record, dict) or set(record) != {"cell", "blocked"}:
                raise GridError(
                    f"changes[{index}] must contain exactly 'cell' and 'blocked'"
                )

            cell = self.validate_position(
                record["cell"], label=f"changes[{index}].cell", require_open=False
            )
            blocked = record["blocked"]
            if not isinstance(blocked, bool):
                raise GridError(f"changes[{index}].blocked must be a boolean")
            if cell in protected_cells and blocked:
                raise GridError(f"protected cell {cell} cannot be blocked")

            previous = updates.get(cell, missing)
            if previous is not missing and previous != blocked:
                raise GridError(f"conflicting updates for cell {cell}")
            updates[cell] = blocked

        for cell in protected_cells:
            final_blocked = updates.get(cell, cell in self.blocked)
            if final_blocked:
                raise GridError(f"protected cell {cell} cannot remain blocked")

        changed = {
            cell
            for cell, should_block in updates.items()
            if (cell in self.blocked) != should_block
        }
        for cell in changed:
            if updates[cell]:
                self.blocked.add(cell)
            else:
                self.blocked.remove(cell)

        if changed:
            self._revision += 1
        return changed
