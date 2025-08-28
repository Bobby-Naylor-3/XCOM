# game/world/pathing.py
from __future__ import annotations
from collections import deque
from typing import Callable

Coord = tuple[int, int]

def flood_fill(
    start: Coord,
    passable: Callable[[int, int], bool],
    max_cost: int,
) -> tuple[dict[Coord, int], dict[Coord, Coord]]:
    """
    4-way BFS from start up to max_cost (cost = 1 per step).
    Returns (costs, parents).
    """
    costs: dict[Coord, int] = {start: 0}
    parents: dict[Coord, Coord] = {}

    q: deque[Coord] = deque([start])
    while q:
        c, r = q.popleft()
        base = costs[(c, r)]
        if base >= max_cost:
            continue

        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if not passable(nc, nr):
                continue
            if (nc, nr) in costs:
                continue
            costs[(nc, nr)] = base + 1
            parents[(nc, nr)] = (c, r)
            q.append((nc, nr))

    return costs, parents

def reconstruct_path(end: Coord, parents: dict[Coord, Coord]) -> list[Coord]:
    """Walk parents back to root; returns [start .. end]. If no path, empty list."""
    path: list[Coord] = []
    cur = end
    while cur in parents:
        path.append(cur)
        cur = parents[cur]
    path.append(cur)  # start
    path.reverse()
    return path
