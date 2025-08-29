# game/entities/player.py
from __future__ import annotations
import pygame
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from game import settings
from game.world.grid import Grid
from game.world.camera import Camera2D

Coord = tuple[int, int]

@dataclass(slots=True)
class Player:
    grid: Grid
    col: int = 3
    row: int = 3
    radius_px: int = max(6, settings.TILE_SIZE // 3)

    # actions
    actions_remaining: int = settings.ACTIONS_PER_TURN

    # movement state
    move_speed_tiles: float = settings.PLAYER_MOVE_SPEED_TPS
    _move_queue: List[Coord] = field(default_factory=list, init=False)   # remaining tile coords (excluding current)
    _move_from: Optional[Coord] = field(default=None, init=False)
    _move_to: Optional[Coord] = field(default=None, init=False)
    _move_t: float = field(default=0.0, init=False)  # 0..1 along current segment

    # -------- movement control --------
    def is_moving(self) -> bool:
        return self._move_to is not None

    def start_move(self, path: List[Coord], speed_tiles: float | None = None) -> None:
        """path must be [start .. end]."""
        if len(path) <= 1:
            return
        if speed_tiles is not None:
            self.move_speed_tiles = speed_tiles
        # queue excludes the first (current) node
        self._move_queue = list(path[1:])
        self._prime_next_segment()

    def _prime_next_segment(self) -> None:
        if not self._move_queue:
            self._move_from = None
            self._move_to = None
            self._move_t = 0.0
            return
        self._move_from = (self.col, self.row)
        self._move_to = self._move_queue.pop(0)
        self._move_t = 0.0

    def update(self, dt: float) -> None:
        if self._move_to is None or self._move_from is None:
            return
        # progress along one tile
        self._move_t += (self.move_speed_tiles * dt)
        if self._move_t >= 1.0:
            # arrive at next tile
            self.col, self.row = self._move_to
            self._move_from = None
            self._move_to = None
            self._move_t = 0.0
            self._prime_next_segment()

    # -------- rendering helpers --------
    def _render_center_world(self) -> Tuple[float, float]:
        if self._move_to is not None and self._move_from is not None:
            fx, fy = self.grid.center_px(*self._move_from)
            tx, ty = self.grid.center_px(*self._move_to)
            t = self._move_t
            return (fx + (tx - fx) * t, fy + (ty - fy) * t)
        return self.grid.center_px(self.col, self.row)

    def draw(self, surface: pygame.Surface, camera: Camera2D, alpha: float = 0.0) -> None:
        cx_w, cy_w = self._render_center_world()
        cx_s, cy_s = camera.world_to_screen(cx_w, cy_w)
        pygame.draw.circle(surface, settings.PLAYER_COLOR, (int(cx_s), int(cy_s)), self.radius_px)

    def draw_selected(self, surface: pygame.Surface, camera: Camera2D, alpha: float = 0.0) -> None:
        cx_w, cy_w = self._render_center_world()
        cx_s, cy_s = camera.world_to_screen(cx_w, cy_w)
        ring_radius = int(self.radius_px * 1.1)
        pygame.draw.circle(surface, (0, 200, 255), (int(cx_s), int(cy_s)), ring_radius, width=2)
        pygame.draw.circle(surface, (0, 120, 200), (int(cx_s), int(cy_s)), ring_radius + 3, width=1)
