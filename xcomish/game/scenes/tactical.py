# game/scenes/tactical.py
from __future__ import annotations
import math
import pygame
from dataclasses import dataclass, field
from game import settings
from game.world.grid import Grid
from game.world.camera import Camera2D
from game.entities.player import Player

@dataclass
class TacticalScene:
    """Tactical layer: world grid + player + camera pan."""
    screen: pygame.Surface
    grid: Grid = field(default_factory=Grid)
    player: Player = field(init=False)
    camera: Camera2D = field(init=False)

    # drag state
    _dragging: bool = field(default=False, init=False)
    _drag_start_screen: tuple[int, int] | None = field(default=None, init=False)
    _drag_start_offset: tuple[float, float] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.player = Player(self.grid)
        world_w = self.grid.cols * self.grid.tile_size
        world_h = self.grid.rows * self.grid.tile_size
        sw, sh = self.screen.get_size()
        self.camera = Camera2D(world_w, world_h, sw, sh)

        # Start centered on the player
        px, py = self.grid.center_px(self.player.col, self.player.row)
        self.camera.center_on_px(px, py)

    # ---- Input ----
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        # Mouse drag to pan (middle or right)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in settings.MOUSE_DRAG_BUTTONS:
            self._dragging = True
            self._drag_start_screen = event.pos
            self._drag_start_offset = (self.camera.offset_x, self.camera.offset_y)

        if event.type == pygame.MOUSEBUTTONUP and event.button in settings.MOUSE_DRAG_BUTTONS:
            self._dragging = False
            self._drag_start_screen = None
            self._drag_start_offset = None

        if event.type == pygame.MOUSEMOTION and self._dragging and self._drag_start_screen and self._drag_start_offset:
            sx, sy = self._drag_start_screen
            ox0, oy0 = self._drag_start_offset
            mx, my = event.pos
            dx, dy = (mx - sx), (my - sy)
            # Camera offset moves opposite to mouse drag direction
            self.camera.set_offset(ox0 - dx, oy0 - dy)

    # ---- Fixed update ----
    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN]  or keys[pygame.K_s]) - (keys[pygame.K_UP]   or keys[pygame.K_w])

        if dx or dy:
            # keep diagonal speed consistent
            length = math.hypot(dx, dy)
            nx, ny = (dx / length, dy / length) if length else (0.0, 0.0)
            speed = settings.CAMERA_PAN_SPEED * (settings.CAMERA_FAST_MULT if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 1.0)
            self.camera.move(nx * speed * dt, ny * speed * dt)

    # ---- Render ----
    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        surface.fill(settings.BG_COLOR)
        self.grid.draw_lines(surface, self.camera)
        self.player.draw(surface, self.camera, alpha=alpha)
        self.grid.draw_highlight(surface, self.camera, pygame.mouse.get_pos())
