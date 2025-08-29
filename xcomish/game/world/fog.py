# game/world/fog.py
from __future__ import annotations
from typing import Set, Iterable
from game.world.los import bresenham_line, los_clear, Coord

def tiles_in_radius(origin: Coord, radius: int) -> Iterable[Coord]:
    ox, oy = origin
    r = radius
    for y in range(oy - r, oy + r + 1):
        for x in range(ox - r, ox + r + 1):
            # Chebyshev radius: square circle. Cheap and gamey.
            if max(abs(x - ox), abs(y - oy)) <= r:
                yield (x, y)

def compute_visible(grid, origin: Coord, radius: int) -> set[Coord]:
    vis: set[Coord] = set()
    for c in tiles_in_radius(origin, radius):
        if not grid.in_bounds(*c):
            continue
        if los_clear(grid, origin, c):
            vis.add(c)
    return vis
