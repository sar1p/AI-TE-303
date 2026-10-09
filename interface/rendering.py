"""Small HTML grid renderer using only validated numeric map coordinates."""

from html import escape

from search_algorithm.grid import Grid
from search_algorithm.models import Position


def grid_html(grid: Grid, path: list[Position], start: Position, goal: Position) -> str:
    order = {cell: index for index, cell in enumerate(path)}
    cells = ['<div class="route-axis"></div>']
    cells.extend(f'<div class="route-axis">{column}</div>' for column in range(grid.width))
    for row in range(grid.height):
        cells.append(f'<div class="route-axis">{row}</div>')
        for column in range(grid.width):
            cell = (row, column)
            kind, label = "open", ""
            if cell in grid.blocked:
                kind, label = "blocked", ""
            elif cell in order:
                kind, label = "path", str(order[cell])
            if cell == goal:
                kind, label = "goal", "G"
            if cell == start:
                kind, label = "robot", "R" if start != goal else "R/G"
            title = escape(f"Row {row}, column {column}: {kind}")
            cells.append(f'<div class="route-cell route-{kind}" title="{title}">{label}</div>')
    return f"""
    <style>
    .route-map {{overflow-x:auto; padding:8px 0 12px;}}
    .route-grid {{display:grid; grid-template-columns:24px repeat({grid.width},minmax(22px,1fr));
        gap:4px; min-width:{24 + grid.width * 26}px; max-width:100%;}}
    .route-cell {{aspect-ratio:1; display:flex; align-items:center; justify-content:center;
        border-radius:5px; font:600 12px ui-monospace,monospace; border:1px solid #263c51;}}
    .route-axis {{display:flex; align-items:center; justify-content:center;
        color:#a5b8cc; font:11px ui-monospace,monospace;}}
    .route-open {{background:#152638;}}
    .route-blocked {{background:repeating-linear-gradient(135deg,#415266,#415266 4px,#344458 4px,#344458 8px);}}
    .route-path {{background:#143f44; border-color:#40b9b0; color:#a8fff1;}}
    .route-robot {{background:#42d1b4; color:#081b21; border-color:#a4ffe3;}}
    .route-goal {{background:#f6bd61; color:#20190c; border-color:#ffe0a7;}}
    .route-legend {{display:flex; flex-wrap:wrap; gap:18px; font:12px sans-serif; color:#c6d7e7;}}
    .route-dot {{display:inline-block; width:11px; height:11px; border-radius:3px; margin-right:6px;}}
    </style>
    <div class="route-map" role="img" aria-label="Warehouse map with robot, goal, obstacles, and route">
      <div class="route-grid">{''.join(cells)}</div>
    </div>
    <div class="route-legend">
      <span><i class="route-dot" style="background:#42d1b4"></i>Robot (R)</span>
      <span><i class="route-dot" style="background:#f6bd61"></i>Goal (G)</span>
      <span><i class="route-dot" style="background:#40b9b0"></i>Route / step number</span>
      <span><i class="route-dot" style="background:#415266"></i>Blocked cell</span>
    </div>
    """
