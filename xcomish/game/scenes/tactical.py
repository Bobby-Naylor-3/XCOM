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
    """Tactical layer: select, preview ranges/paths, plan, confirm to animate & consume actions."""
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

    # planned destination (no movement until confirmed)
    _planned_target: Coord | None = field(default=None, init=False)
    _planned_path: list[Coord] = field(default_factory=list, init=False)
    _planned_actions: int | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.player = Player(self.grid)
        world_w = self.grid.cols * self.grid.tile_size
        world_h = self.grid.rows * self.grid.tile_size
        sw, sh = self.screen.get_size()
        self.camera = Camera2D(world_w, world_h, sw, sh)

        # Start centered on the player
        px, py = self.grid.center_px(self.player.col, self.player.row)
        self.camera.center_on_px(px, py)

        self._font = pygame.font.Font(None, settings.HUD_FONT_SIZE)

    # ---- Input ----
    def handle_event(self, event: pygame.event.Event) -> None:
        # quit
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        # test helper: new turn (refill actions + recompute ranges if selected)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_n:
            self.player.actions_remaining = settings.ACTIONS_PER_TURN
            if self._selected:
                self._compute_ranges(force=True)

        # confirm move: Enter / Space (only if we have a plan and not moving)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self._selected and self._planned_path and not self.player.is_moving():
                self._confirm_plan()

        # right-click cancels plan
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._clear_plan()

        # camera drag (middle or right — keep right for pan + plan cancel via key)
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

        # left-click: select/deselect or set plan (disabled while moving)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.player.is_moving():
            world_x, world_y = self.camera.screen_to_world(*event.pos)
            col, row = self.grid.from_px(world_x, world_y)

            if (col, row) == (self.player.col, self.player.row):
                # toggle selection
                if not self._selected:
                    self._selected = True
                    self._compute_ranges()
                else:
                    self._selected = False
                    self._range_costs.clear()
                    self._range_parents.clear()
                    self._clear_plan()
                return

            if self._selected and self._range_costs:
                self._try_set_plan((col, row))
            else:
                self._selected = False
                self._clear_plan()
                self._range_costs.clear()
                self._range_parents.clear()

    # ---- Planning / ranges ----
    def _compute_ranges(self, force: bool = False) -> None:
        start: Coord = (self.player.col, self.player.row)

        def passable(c: int, r: int) -> bool:
            return self.grid.in_bounds(c, r)  # later: obstacles

        # respect remaining actions
        if self.player.actions_remaining <= 0:
            self._range_costs, self._range_parents = {start: 0}, {}
            return

        max_cost = settings.MOVE_RANGE_1 if self.player.actions_remaining == 1 else settings.MOVE_RANGE_2
        self._range_costs, self._range_parents = flood_fill(start, passable, max_cost)
        if force:
            # keep current plan if still valid; otherwise clear it
            if self._planned_target and self._planned_target not in self._range_costs:
                self._clear_plan()

    def _actions_for_cost(self, cost: int | None) -> int | None:
        if cost is None:
            return None
        if cost <= settings.MOVE_RANGE_1:
            return 1
        if cost <= settings.MOVE_RANGE_2:
            return 2
        return None

    def _try_set_plan(self, target: Coord) -> None:
        cost = self._range_costs.get(target)
        actions = self._actions_for_cost(cost)
        if actions is None:
            self._clear_plan()
            return
        path = reconstruct_path(target, self._range_parents)
        if not path:
            self._clear_plan()
            return
        self._planned_target = target
        self._planned_path = path
        self._planned_actions = actions

    def _clear_plan(self) -> None:
        self._planned_target = None
        self._planned_path.clear()
        self._planned_actions = None

    def _confirm_plan(self) -> None:
        """Consume actions and start movement animation along the planned path."""
        if not self._planned_path or self._planned_actions is None:
            return
        if self._planned_actions > self.player.actions_remaining:
            # not enough actions → ignore
            return
        # pay actions up front and go
        self.player.actions_remaining -= self._planned_actions
        self.player.start_move(self._planned_path, settings.PLAYER_MOVE_SPEED_TPS)

    # ---- Fixed update ----
    def update(self, dt: float) -> None:
        # camera pan
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN]  or keys[pygame.K_s]) - (keys[pygame.K_UP]   or keys[pygame.K_w])
        if dx or dy:
            length = math.hypot(dx, dy)
            nx, ny = (dx / length, dy / length) if length else (0.0, 0.0)
            speed = settings.CAMERA_PAN_SPEED * (settings.CAMERA_FAST_MULT if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 1.0)
            self.camera.move(nx * speed * dt, ny * speed * dt)

        # update player animation
        was_moving = self.player.is_moving()
        self.player.update(dt)
        now_moving = self.player.is_moving()

        # when movement finishes, clear plan and recompute ranges (respect remaining actions)
        if was_moving and not now_moving:
            self._clear_plan()
            if self._selected:
                self._compute_ranges()

    # ---- Render ----
    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        surface.fill(settings.BG_COLOR)
        self.grid.draw_lines(surface, self.camera)

        # range overlays (hide while moving)
        if self._selected and self._range_costs and not self.player.is_moving():
            self._draw_range_overlays(surface)

        # player
        self.player.draw(surface, self.camera, alpha=alpha)
        if self._selected:
            self.player.draw_selected(surface, self.camera, alpha=alpha)

        # planned path (if not moving yet)
        if self._selected and self._planned_path and not self.player.is_moving():
            self._draw_planned_path(surface)

        # hover path on top (only when not moving)
        if self._selected and self._range_costs and not self.player.is_moving():
            self._draw_hover_path(surface)

        # mouse tile highlight
        self.grid.draw_highlight(surface, self.camera, pygame.mouse.get_pos())

        # HUD
        self._draw_action_hud(surface)

    # ---- Overlay helpers ----
    def _draw_range_overlays(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for (c, r), cost in self._range_costs.items():
            rect = self.grid.tile_rect_screen(self.camera, c, r)
            if not rect.colliderect(pygame.Rect(0, 0, sw, sh)):
                continue
            overlay.fill(settings.RANGE1_RGBA if cost <= settings.MOVE_RANGE_1 else settings.RANGE2_RGBA, rect)
        # don't tint current tile
        p_rect = self.grid.tile_rect_screen(self.camera, self.player.col, self.player.row)
        overlay.fill((0, 0, 0, 0), p_rect)
        surface.blit(overlay, (0, 0))

    def _draw_hover_path(self, surface: pygame.Surface) -> None:
        mx, my = pygame.mouse.get_pos()
        wx, wy = self.camera.screen_to_world(mx, my)
        tc, tr = self.grid.from_px(wx, wy)
        cost = self._range_costs.get((tc, tr))
        actions = self._actions_for_cost(cost)
        if actions is None:
            return
        path = reconstruct_path((tc, tr), self._range_parents)
        if not path:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pts = [self.camera.world_to_screen(*self.grid.center_px(c, r)) for c, r in path]
        if len(pts) >= 2:
            pygame.draw.lines(overlay, settings.PATH_RGBA, False, pts, width=6)
        tgt_rect = self.grid.tile_rect_screen(self.camera, tc, tr)
        pygame.draw.rect(overlay, settings.PATH_RGBA, tgt_rect, width=3)
        surface.blit(overlay, (0, 0))

    def _draw_planned_path(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pts = [self.camera.world_to_screen(*self.grid.center_px(c, r)) for c, r in self._planned_path]
        if len(pts) >= 2:
            pygame.draw.lines(overlay, settings.PLAN_RGBA, False, pts, width=8)
        tc, tr = self._planned_target  # type: ignore
        tgt_rect = self.grid.tile_rect_screen(self.camera, tc, tr)
        pygame.draw.rect(overlay, settings.PLAN_RGBA, tgt_rect, width=4)
        surface.blit(overlay, (0, 0))

    def _draw_action_hud(self, surface: pygame.Surface) -> None:
        # base text: actions remaining
        text = f"Actions: {self.player.actions_remaining}/{settings.ACTIONS_PER_TURN}"

        # plan/hover info
        extra = None
        if not self.player.is_moving():
            if self._planned_actions is not None and self._planned_path:
                steps = max(0, len(self._planned_path) - 1)
                extra = f"Planned: {'1 Action' if self._planned_actions == 1 else '2 Actions (Dash)'} · {steps} tiles (Enter/Space to confirm)"
            else:
                mx, my = pygame.mouse.get_pos()
                wx, wy = self.camera.screen_to_world(mx, my)
                tc, tr = self.grid.from_px(wx, wy)
                cost = self._range_costs.get((tc, tr))
                actions = self._actions_for_cost(cost)
                if actions is not None:
                    extra = f"Hover: {'1 Action' if actions == 1 else '2 Actions (Dash)'} · {cost} tiles"

        if extra:
            text = f"{text}    |    {extra}"

        pad = 8
        surf_text = self._font.render(text, True, settings.HUD_TEXT_RGB)
        w, h = surf_text.get_size()
        pill = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        pill.fill(settings.HUD_BG_RGBA)
        pill.blit(surf_text, (pad, pad))
        surface.blit(pill, (10, 10))
