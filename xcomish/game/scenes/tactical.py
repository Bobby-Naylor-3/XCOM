# game/scenes/tactical.py
from __future__ import annotations
import math
import pygame
from dataclasses import dataclass, field
from game import settings
from game.world.grid import Grid
from game.world.camera import Camera2D
from game.entities.player import Player
from game.world.pathing import flood_fill, reconstruct_path

Coord = tuple[int, int]

@dataclass
class TacticalScene:
    """Tactical layer: world grid + player + camera pan + selection/range preview."""
    screen: pygame.Surface
    grid: Grid = field(default_factory=Grid)
    player: Player = field(init=False)
    camera: Camera2D = field(init=False)

    # drag state
    _dragging: bool = field(default=False, init=False)
    _drag_start_screen: tuple[int, int] | None = field(default=None, init=False)
    _drag_start_offset: tuple[float, float] | None = field(default=None, init=False)

    # selection + range cache
    _selected: bool = field(default=False, init=False)
    _range_costs: dict[Coord, int] = field(default_factory=dict, init=False)
    _range_parents: dict[Coord, Coord] = field(default_factory=dict, init=False)

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
            self.camera.set_offset(ox0 - dx, oy0 - dy)

        # Left-click selects player (or deselect if anywhere else)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            world_x, world_y = self.camera.screen_to_world(*event.pos)
            col, row = self.grid.from_px(world_x, world_y)
            if (col, row) == (self.player.col, self.player.row):
                self._selected = True
                self._compute_ranges()
            else:
                # click elsewhere: just deselect for now (no move yet)
                self._selected = False
                self._range_costs.clear()
                self._range_parents.clear()

    def _compute_ranges(self) -> None:
        start: Coord = (self.player.col, self.player.row)

        def passable(c: int, r: int) -> bool:
            return self.grid.in_bounds(c, r)  # later: check obstacles, units, etc.

        max_cost = settings.MOVE_RANGE_2
        self._range_costs, self._range_parents = flood_fill(start, passable, max_cost)

    # ---- Fixed update ----
    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN]  or keys[pygame.K_s]) - (keys[pygame.K_UP]   or keys[pygame.K_w])

        if dx or dy:
            length = math.hypot(dx, dy)
            nx, ny = (dx / length, dy / length) if length else (0.0, 0.0)
            speed = settings.CAMERA_PAN_SPEED * (settings.CAMERA_FAST_MULT if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 1.0)
            self.camera.move(nx * speed * dt, ny * speed * dt)

    # ---- Render ----
    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        surface.fill(settings.BG_COLOR)
        self.grid.draw_lines(surface, self.camera)

        # Range overlays (under units)
        if self._selected and self._range_costs:
            self._draw_range_overlays(surface)

        # Player
        self.player.draw(surface, self.camera, alpha=alpha)
        if self._selected:
            self.player.draw_selected(surface, self.camera, alpha=alpha)

        # Hover path (on top)
        if self._selected and self._range_costs:
            self._draw_hover_path(surface)

        # Mouse tile highlight last
        self.grid.draw_highlight(surface, self.camera, pygame.mouse.get_pos())

    # ---- Overlay helpers ----
    def _draw_range_overlays(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)

        # Draw cyan for <= MOVE_RANGE_1, yellow for (MOVE_RANGE_1, MOVE_RANGE_2]
        for (c, r), cost in self._range_costs.items():
            rect = self.grid.tile_rect_screen(self.camera, c, r)
            if not rect.colliderect(pygame.Rect(0, 0, sw, sh)):
                continue
            if cost <= settings.MOVE_RANGE_1:
                overlay.fill(settings_RANGE1 := settings.RANGE1_RGBA, rect)
            else:
                overlay.fill(settings_RANGE2 := settings.RANGE2_RGBA, rect)

        # Don't tint the player's own tile (optional)
        p_rect = self.grid.tile_rect_screen(self.camera, self.player.col, self.player.row)
        overlay.fill((0, 0, 0, 0), p_rect)

        surface.blit(overlay, (0, 0))

    def _draw_hover_path(self, surface: pygame.Surface) -> None:
        mx, my = pygame.mouse.get_pos()
        wx, wy = self.camera.screen_to_world(mx, my)
        tc, tr = self.grid.from_px(wx, wy)

        cost = self._range_costs.get((tc, tr))
        if cost is None or cost > settings.MOVE_RANGE_2:
            return  # not reachable

        path = reconstruct_path((tc, tr), self._range_parents)
        if not path:
            return

        # Convert centers to screen pixels
        pts: list[tuple[int, int]] = []
        for c, r in path:
            cx_w, cy_w = self.grid.center_px(c, r)
            cx_s, cy_s = self.camera.world_to_screen(cx_w, cy_w)
            pts.append((cx_s, cy_s))

        # Draw a thick polyline
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        if len(pts) >= 2:
            pygame.draw.lines(overlay, settings.PATH_RGBA, False, pts, width=6)

        # Emphasize hovered target tile
        tgt_rect = self.grid.tile_rect_screen(self.camera, tc, tr)
        pygame.draw.rect(overlay, settings.PATH_RGBA, tgt_rect, width=3)

        surface.blit(overlay, (0, 0))
