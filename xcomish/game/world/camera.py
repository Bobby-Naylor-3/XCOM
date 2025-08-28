# game/world/camera.py
from __future__ import annotations
from dataclasses import dataclass
import pygame

@dataclass(slots=True)
class Camera2D:
    world_w: int
    world_h: int
    screen_w: int
    screen_h: int
    offset_x: float = 0.0
    offset_y: float = 0.0

    def _clamp(self) -> None:
        max_x = max(0, self.world_w - self.screen_w)
        max_y = max(0, self.world_h - self.screen_h)
        self.offset_x = min(max(0.0, self.offset_x), float(max_x))
        self.offset_y = min(max(0.0, self.offset_y), float(max_y))

    def set_offset(self, x: float, y: float) -> None:
        self.offset_x, self.offset_y = x, y
        self._clamp()

    def move(self, dx: float, dy: float) -> None:
        self.offset_x += dx
        self.offset_y += dy
        self._clamp()

    # Conversions
    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        return int(x - self.offset_x), int(y - self.offset_y)

    def screen_to_world(self, x: float, y: float) -> tuple[int, int]:
        return int(x + self.offset_x), int(y + self.offset_y)

    def view_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.offset_x), int(self.offset_y), self.screen_w, self.screen_h)

    # Helpers for centering on something (e.g. a tile center in px)
    def center_on_px(self, cx: int, cy: int) -> None:
        self.set_offset(cx - self.screen_w // 2, cy - self.screen_h // 2)
