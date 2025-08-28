# game/world/grid.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from game import settings
from game.world.camera import Camera2D

@dataclass(slots=True)
class Grid:
    cols: int = settings.WORLD_COLS
    rows: int = settings.WORLD_ROWS
    tile_size: int = settings.TILE_SIZE

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

    # --- drawing ---
    def draw_lines(self, surface: pygame.Surface, camera: Camera2D) -> None:
        ts = self.tile_size
        sw, sh = surface.get_size()
        ox, oy = camera.offset_x, camera.offset_y

        # Visible column/row range
        first_c = max(0, int(ox // ts))
        last_c  = min(self.cols, int((ox + sw) // ts) + 1)
        first_r = max(0, int(oy // ts))
        last_r  = min(self.rows, int((oy + sh) // ts) + 1)

        color = settings.GRID_COLOR

        # Vertical lines
        for c in range(first_c, last_c + 1):
            x_screen = int(c * ts - ox)
            pygame.draw.line(surface, color, (x_screen, 0), (x_screen, sh), 1)

        # Horizontal lines
        for r in range(first_r, last_r + 1):
            y_screen = int(r * ts - oy)
            pygame.draw.line(surface, color, (0, y_screen), (sw, y_screen), 1)

    def draw_highlight(self, surface: pygame.Surface, camera: Camera2D, mouse_pos: tuple[int, int]) -> None:
        # Convert mouse (screen) to world tile
        world_x, world_y = camera.screen_to_world(*mouse_pos)
        col, row = self.from_px(world_x, world_y)
        if not self.in_bounds(col, row):
            return
        xw, yw = self.to_px(col, row)
        xs, ys = camera.world_to_screen(xw, yw)
        rect = pygame.Rect(xs, ys, self.tile_size, self.tile_size)
        pygame.draw.rect(surface, settings.GRID_HILITE, rect, width=2)

    # Add at bottom of class Grid:
    def tile_rect_screen(self, camera, col: int, row: int) -> pygame.Rect:
        xw, yw = self.to_px(col, row)
        xs, ys = camera.world_to_screen(xw, yw)
        return pygame.Rect(xs, ys, self.tile_size, self.tile_size)

