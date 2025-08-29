# game/world/grid.py
from __future__ import annotations
import pygame
from dataclasses import dataclass, field
from typing import Set, Tuple
from game import settings
from game.world.camera import Camera2D

Coord = tuple[int, int]

@dataclass(slots=True)
class Grid:
    cols: int = settings.WORLD_COLS
    rows: int = settings.WORLD_ROWS
    tile_size: int = settings.TILE_SIZE
    blocked: Set[Coord] = field(default_factory=set)  # <--- NEW

    # --- math ---
    def to_px(self, col: int, row: int) -> tuple[int, int]:
        return col * self.tile_size, row * self.tile_size

    def center_px(self, col: int, row: int) -> tuple[int, int]:
        x, y = self.to_px(col, row)
        half = self.tile_size // 2
        return x + half, y + half

    def from_px(self, x: int, y: int) -> tuple[int, int]:
        return x // self.tile_size, y // self.tile_size

    def in_bounds(self, col: int, row: int) -> bool:
        return 0 <= col < self.cols and 0 <= row < self.rows

    # --- NEW: obstacles / passability ---
    def is_blocked(self, col: int, row: int) -> bool:
        return (col, row) in self.blocked

    def is_passable(self, col: int, row: int) -> bool:
        return self.in_bounds(col, row) and (col, row) not in self.blocked

    def toggle_obstacle(self, col: int, row: int) -> None:
        if not self.in_bounds(col, row):
            return
        if (col, row) in self.blocked:
            self.blocked.remove((col, row))
        else:
            self.blocked.add((col, row))

    # --- drawing ---
    def draw_lines(self, surface: pygame.Surface, camera: Camera2D) -> None:
        ts = self.tile_size
        sw, sh = surface.get_size()
        ox, oy = camera.offset_x, camera.offset_y

        first_c = max(0, int(ox // ts))
        last_c  = min(self.cols, int((ox + sw) // ts) + 1)
        first_r = max(0, int(oy // ts))
        last_r  = min(self.rows, int((oy + sh) // ts) + 1)

        color = settings.GRID_COLOR

        for c in range(first_c, last_c + 1):
            x_screen = int(c * ts - ox)
            pygame.draw.line(surface, color, (x_screen, 0), (x_screen, sh), 1)

        for r in range(first_r, last_r + 1):
            y_screen = int(r * ts - oy)
            pygame.draw.line(surface, color, (0, y_screen), (sw, y_screen), 1)

    def draw_highlight(self, surface: pygame.Surface, camera: Camera2D, mouse_pos: tuple[int, int]) -> None:
        col, row = self.from_px(*camera.screen_to_world(*mouse_pos))
        if not self.in_bounds(col, row):
            return
        xs, ys = camera.world_to_screen(*self.to_px(col, row))
        rect = pygame.Rect(xs, ys, self.tile_size, self.tile_size)
        pygame.draw.rect(surface, settings.GRID_HILITE, rect, width=2)

    # NEW: visible obstacles only
    def draw_obstacles(self, surface: pygame.Surface, camera: Camera2D) -> None:
        sw, sh = surface.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)

        ts = self.tile_size
        ox, oy = camera.offset_x, camera.offset_y
        first_c = max(0, int(ox // ts))
        last_c  = min(self.cols, int((ox + sw) // ts) + 1)
        first_r = max(0, int(oy // ts))
        last_r  = min(self.rows, int((oy + sh) // ts) + 1)

        for c in range(first_c, last_c):
            for r in range(first_r, last_r):
                if (c, r) in self.blocked:
                    rect = self.tile_rect_screen(camera, c, r)
                    overlay.fill(settings.OBSTACLE_RGBA, rect)
                    pygame.draw.rect(overlay, settings.OBSTACLE_BORDER_RGB, rect, width=1)

        surface.blit(overlay, (0, 0))

    # (you already had this helper)
    def tile_rect_screen(self, camera, col: int, row: int) -> pygame.Rect:
        xw, yw = self.to_px(col, row)
        xs, ys = camera.world_to_screen(xw, yw)
        return pygame.Rect(xs, ys, self.tile_size, self.tile_size)
