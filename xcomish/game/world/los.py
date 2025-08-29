# game/world/los.py
from __future__ import annotations
from typing import Iterable, Iterator, Tuple

Coord = tuple[int, int]

def bresenham_line(a: Coord, b: Coord) -> Iterator[Coord]:
    """Tiles from a to b inclusive using Bresenham (4-connected)."""
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        yield (x0, y0)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy

def los_clear(grid, a: Coord, b: Coord) -> bool:
    """True if the straight line from a to b has no *blocked* tiles between them."""
    it = iter(bresenham_line(a, b))
    next(it, None)  # skip the source tile
    for c in it:
        if c == b:
            return True
        if not grid.is_passable(*c):
            return False
    return True

def facing_side(from_: Coord, to: Coord) -> str:
    """Which side of the 'to' tile faces 'from_': 'N','E','S','W' by dominant axis."""
    fx, fy = from_
    tx, ty = to
    dx = tx - fx
    dy = ty - fy
    if abs(dx) >= abs(dy):
        return "W" if dx < 0 else "E"
    else:
        return "N" if dy < 0 else "S"
