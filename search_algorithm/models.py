"""Shared search results with portable, strict JSON serialization."""

from dataclasses import asdict, dataclass, field
from typing import Literal

Position = tuple[int, int]
SearchStatus = Literal["found", "unreachable", "invalid_input"]


@dataclass
class SearchMetrics:
    """Counters for one plan call, including pending queue operations."""

    processed_states: int = 0
    queue_pops: int = 0
    queue_pushes: int = 0
    elapsed_ms: float = 0.0


@dataclass
class SearchResult:
    status: SearchStatus
    path: list[Position] = field(default_factory=list)
    cost: int | None = None
    metrics: SearchMetrics = field(default_factory=SearchMetrics)
    message: str = ""

    def to_dict(self) -> dict:
        result = asdict(self)
        result["path"] = [list(cell) for cell in self.path]
        return result
