# game/world/cover.py
from __future__ import annotations
from typing import Literal
from game.world.grid import Grid

Side = Literal["N", "E", "S", "W"]
CoverType = Literal["none", "half", "full"]

SIDES: tuple[Side, ...] = ("N", "E", "S", "W")
DIRS: dict[Side, tuple[int, int]] = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}
DIAGS: dict[Side, tuple[tuple[int, int], tuple[int, int]]] = {
    "N": ((-1, -1), (1, -1)),
    "E": ((1, -1), (1, 1)),
    "S": ((-1, 1), (1, 1)),
    "W": ((-1, -1), (-1, 1)),
}

def compute_tile_cover(
    grid: Grid, col: int, row: int, *, oob_is_full: bool = True
) -> dict[Side, CoverType]:
    cover: dict[Side, CoverType] = {"N": "none", "E": "none", "S": "none", "W": "none"}
    for side in SIDES:
        dc, dr = DIRS[side]
        ac, ar = col + dc, row + dr  # adjacent in cardinal direction

        # Full cover if adjacent is blocked or OOB (if enabled)
        adj_in = grid.in_bounds(ac, ar)
        if (adj_in and grid.is_blocked(ac, ar)) or (not adj_in and oob_is_full):
            cover[side] = "full"
            continue

        # Half cover if any diagonal near that side is blocked (and adj isn't)
        for (dc2, dr2) in DIAGS[side]:
            c2, r2 = col + dc2, row + dr2
            if grid.in_bounds(c2, r2) and grid.is_blocked(c2, r2):
                cover[side] = "half"
                break

    return cover

def cover_to_label(cv: dict[Side, CoverType]) -> str:
    order = ("N", "E", "S", "W")
    parts: list[str] = []
    for s in order:
        v = cv[s]
        if v != "none":
            parts.append(f"{s}:{'F' if v=='full' else 'H'}")
    return " ".join(parts) if parts else "None"
