# game/scenes/tactical.py (merged)
from __future__ import annotations
import math, random
import pygame
from dataclasses import dataclass, field
from typing import Optional

from game import settings
from game.world.grid import Grid
from game.world.camera import Camera2D
from game.entities.player import Player
from game.entities.enemy import Enemy
from game.world.pathing import flood_fill, reconstruct_path
from game.world.cover import compute_tile_cover, cover_to_label
from game.world.los import los_clear, facing_side, Coord
from game.world.fog import compute_visible
from game.combat.hit import compute_hit
from game.combat.resolve import preview_probabilities, resolve_shot


@dataclass
class TacticalScene:
    """
    Tactical layer:
    - Selection, planning, and confirming moves
    - Obstacles editor + demo seeding (Shift+O)
    - Enemy placement editor
    - Cover (pips + labels), LoF/Flanking, distance
    - Fog of war (visible vs explored)
    - Shot preview (hit/crit/graze/damage) and F to fire with RNG-backed resolution
    """
    screen: pygame.Surface
    grid: Grid = field(default_factory=Grid)
    player: Player = field(init=False)
    camera: Camera2D = field(init=False)

    # drag
    _dragging: bool = field(default=False, init=False)
    _drag_start_screen: tuple[int, int] | None = field(default=None, init=False)
    _drag_start_offset: tuple[float, float] | None = field(default=None, init=False)

    # selection + range
    _selected: bool = field(default=False, init=False)
    _range_costs: dict[Coord, int] = field(default_factory=dict, init=False)
    _range_parents: dict[Coord, Coord] = field(default_factory=dict, init=False)

    # plan
    _planned_target: Coord | None = field(default=None, init=False)
    _planned_path: list[Coord] = field(default_factory=list, init=False)
    _planned_actions: int | None = field(default=None, init=False)

    # edit modes
    _obstacle_edit: bool = field(default=False, init=False)
    _enemy_edit: bool = field(default=False, init=False)

    # enemies
    _enemies: dict[Coord, Enemy] = field(default_factory=dict, init=False)

    # fog
    _visible: set[Coord] = field(default_factory=set, init=False)
    _explored: set[Coord] = field(default_factory=set, init=False)

    # combat RNG + last shot text
    _rng: random.Random = field(default_factory=random.Random, init=False)
    _last_shot_text: str | None = field(default=None, init=False)

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
        # RNG seed (optional)
        self._rng = random.Random(settings.RNG_SEED) if settings.RNG_SEED is not None else random.Random()
        self._recompute_visibility()

    # ---- Input ----
    def handle_event(self, event: pygame.event.Event) -> None:
        # quit
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        # modes
        if event.type == pygame.KEYDOWN and event.key == pygame.K_o:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                self._seed_demo_obstacles()
            else:
                self._obstacle_edit = not self._obstacle_edit
                if self._obstacle_edit:
                    self._enemy_edit = False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            self._enemy_edit = not self._enemy_edit
            if self._enemy_edit:
                self._obstacle_edit = False

        # new turn for testing
        if event.type == pygame.KEYDOWN and event.key == pygame.K_n:
            self.player.actions_remaining = settings.ACTIONS_PER_TURN
            if self._selected:
                self._compute_ranges(force=True)

        # confirm move
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self._selected and self._planned_path and not self.player.is_moving():
                self._confirm_plan()

        # FIRE!
        if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            enemy = self._enemy_under_mouse()
            if enemy and (enemy.col, enemy.row) in self._visible:
                res = resolve_shot(self.grid, (self.player.col, self.player.row), (enemy.col, enemy.row), self._rng)
                if res.outcome in ("hit", "crit", "graze") and res.damage > 0:
                    enemy.apply_damage(res.damage)
                    if enemy.is_dead():
                        del self._enemies[(enemy.col, enemy.row)]
                # Last-shot HUD line
                self._last_shot_text = self._format_last_shot(res)

        # cancel plan
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._clear_plan()

        # camera drag
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

        # left-click (editor priority)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.player.is_moving():
            world_x, world_y = self.camera.screen_to_world(*event.pos)
            col, row = self.grid.from_px(world_x, world_y)

            if self._obstacle_edit:
                if (col, row) != (self.player.col, self.player.row) and (col, row) not in self._enemies:
                    self.grid.toggle_obstacle(col, row)
                    if self._selected:
                        self._compute_ranges(force=True)
                    self._recompute_visibility()
                return

            if self._enemy_edit:
                if (col, row) != (self.player.col, self.player.row) and self.grid.is_passable(col, row):
                    key = (col, row)
                    if key in self._enemies:
                        del self._enemies[key]
                    else:
                        self._enemies[key] = Enemy(self.grid, col, row)
                return

            # selection / planning
            if (col, row) == (self.player.col, self.player.row):
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
            return self.grid.is_passable(c, r) and ((c, r) not in self._enemies)

        if self.player.actions_remaining <= 0:
            self._range_costs, self._range_parents = {start: 0}, {}
            return

        max_cost = settings.MOVE_RANGE_1 if self.player.actions_remaining == 1 else settings.MOVE_RANGE_2
        self._range_costs, self._range_parents = flood_fill(start, passable, max_cost)
        if force and self._planned_target and self._planned_target not in self._range_costs:
            self._clear_plan()

    def _actions_for_cost(self, cost: int | None) -> int | None:
        if cost is None: return None
        if cost <= settings.MOVE_RANGE_1: return 1
        if cost <= settings.MOVE_RANGE_2: return 2
        return None

    def _try_set_plan(self, target: Coord) -> None:
        if not self.grid.is_passable(*target) or target in self._enemies:
            self._clear_plan()
            return
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
        if not self._planned_path or self._planned_actions is None:
            return
        if self._planned_actions > self.player.actions_remaining:
            return
        self.player.actions_remaining -= self._planned_actions
        self.player.start_move(self._planned_path, settings.PLAYER_MOVE_SPEED_TPS)

    # ---- Fog / visibility ----
    def _recompute_visibility(self) -> None:
        origin = (self.player.col, self.player.row)
        self._visible = compute_visible(self.grid, origin, settings.SIGHT_RADIUS_TILES)
        self._explored |= self._visible

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

        # update movement
        old_pos = (self.player.col, self.player.row)
        was_moving = self.player.is_moving()
        self.player.update(dt)
        now_moving = self.player.is_moving()
        if was_moving and not now_moving:
            self._clear_plan()
            if self._selected:
                self._compute_ranges()
        if (self.player.col, self.player.row) != old_pos or was_moving:
            self._recompute_visibility()

    # ---- Render ----
    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        surface.fill(settings.BG_COLOR)
        self.grid.draw_lines(surface, self.camera)
        self.grid.draw_obstacles(surface, self.camera)

        # range overlays (hide while moving)
        if self._selected and self._range_costs and not self.player.is_moving():
            self._draw_range_overlays(surface)

        # enemies
        for enemy in self._enemies.values():
            enemy.draw(surface, self.camera)

        # player
        self.player.draw(surface, self.camera, alpha=alpha)
        if self._selected:
            self.player.draw_selected(surface, self.camera, alpha=alpha)

        # planned/hover path
        if self._selected and self._planned_path and not self.player.is_moving():
            self._draw_planned_path(surface)
        if self._selected and self._range_costs and not self.player.is_moving():
            self._draw_hover_path(surface)

        # cover pips: here + planned + hover (last so on top)
        if self._selected:
            self._draw_cover_for_here(surface)
            if self._planned_target and not self.player.is_moving():
                pc, pr = self._planned_target
                self._draw_cover_pips(surface, pc, pr, focused=True)
            # hover
            mx, my = pygame.mouse.get_pos()
            wx, wy = self.camera.screen_to_world(mx, my)
            hc, hr = self.grid.from_px(wx, wy)
            if (hc, hr) in self._range_costs and not self.player.is_moving():
                self._draw_cover_pips(surface, hc, hr, focused=True)

        # LoF preview line
        self._draw_lof_overlay(surface)

        # Fog
        self._draw_fog(surface)

        # mouse tile highlight (on top)
        self.grid.draw_highlight(surface, self.camera, pygame.mouse.get_pos())

        # HUD
        self._draw_hud(surface)

    # ---- Helpers ----
    def _enemy_under_mouse(self) -> Optional[Enemy]:
        mx, my = pygame.mouse.get_pos()
        wx, wy = self.camera.screen_to_world(mx, my)
        c, r = self.grid.from_px(wx, wy)
        return self._enemies.get((c, r))

    # ---- Overlays ----
    def _draw_range_overlays(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for (c, r), cost in self._range_costs.items():
            rect = self.grid.tile_rect_screen(self.camera, c, r)
            if not rect.colliderect(pygame.Rect(0, 0, sw, sh)):
                continue
            overlay.fill(settings.RANGE1_RGBA if cost <= settings.MOVE_RANGE_1 else settings.RANGE2_RGBA, rect)
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

    def _draw_lof_overlay(self, surface: pygame.Surface) -> None:
        enemy = self._enemy_under_mouse()
        if not enemy:
            return
        tgt = (enemy.col, enemy.row)
        if tgt not in self._visible:
            return
        shooter = (self.player.col, self.player.row)
        has_los = los_clear(self.grid, shooter, tgt)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        sx, sy = self.camera.world_to_screen(*self.grid.center_px(*shooter))
        tx, ty = self.camera.world_to_screen(*self.grid.center_px(*tgt))
        color = settings.LOF_CLEAR_RGBA if has_los else settings.LOF_BLOCKED_RGBA
        pygame.draw.line(overlay, color, (sx, sy), (tx, ty), width=4)
        # Draw target cover pips bright for context
        self._draw_cover_pips(surface, enemy.col, enemy.row, focused=True)
        surface.blit(overlay, (0, 0))

    # ---- Cover drawing ----
    def _draw_cover_for_here(self, surface: pygame.Surface) -> None:
        # Always show cover pips for the player's current tile (dimmed).
        self._draw_cover_pips(surface, self.player.col, self.player.row, focused=False)

    def _draw_cover_pips(self, surface: pygame.Surface, col: int, row: int, *, focused: bool) -> None:
        cv = compute_tile_cover(self.grid, col, row, oob_is_full=settings.COVER_OOB_IS_FULL)
        rect = self.grid.tile_rect_screen(self.camera, col, row)
        if not rect.colliderect(surface.get_rect()):
            return

        full = settings.COVER_FULL_RGB if focused else settings.COVER_DIM_RGB
        half = settings.COVER_HALF_RGB if focused else settings.COVER_DIM_RGB
        alpha = settings.COVER_ALPHA
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        m = settings.COVER_MARGIN
        t = settings.COVER_THICK
        x, y, w, h = rect

        def poly_top():
            return [(x + m, y + m), (x + w - m, y + m), (x + w - m - t, y + m + t), (x + m + t, y + m + t)]
        def poly_right():
            return [(x + w - m, y + m), (x + w - m, y + h - m), (x + w - m - t, y + h - m - t), (x + w - m - t, y + m + t)]
        def poly_bottom():
            return [(x + m, y + h - m), (x + w - m, y + h - m), (x + w - m - t, y + h - m - t), (x + m + t, y + h - m - t)]
        def poly_left():
            return [(x + m, y + m), (x + m, y + h - m), (x + m + t, y + h - m - t), (x + m + t, y + m + t)]

        for side, poly_fn in (("N", poly_top), ("E", poly_right), ("S", poly_bottom), ("W", poly_left)):
            k = cv[side]
            if k == "none":
                continue
            color = full if k == "full" else half
            pygame.draw.polygon(overlay, (*color, alpha), poly_fn())
            surface.blit(overlay, (0, 0))

    # ---- Fog ----
    def _draw_fog(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ts = self.grid.tile_size
        ox, oy = self.camera.offset_x, self.camera.offset_y
        first_c = max(0, int(ox // ts))
        last_c  = min(self.grid.cols, int((ox + sw) // ts) + 1)
        first_r = max(0, int(oy // ts))
        last_r  = min(self.grid.rows, int((oy + sh) // ts) + 1)
        for c in range(first_c, last_c):
            for r in range(first_r, last_r):
                rect = self.grid.tile_rect_screen(self.camera, c, r)
                if (c, r) in self._visible:
                    continue
                rgba = settings.FOG_SOFT_RGBA if (c, r) in self._explored else settings.FOG_HARD_RGBA
                overlay.fill(rgba, rect)
        surface.blit(overlay, (0, 0))

    # ---- HUD ----
    def _draw_hud(self, surface: pygame.Surface) -> None:
        pieces = [f"Actions: {self.player.actions_remaining}/{settings.ACTIONS_PER_TURN}"]
        if self._obstacle_edit:
            pieces.append("Obstacle Edit (O) | Shift+O demo | LMB toggle")
        if self._enemy_edit:
            pieces.append("Enemy Edit (E) | LMB add/remove")

        # Cover(Here)
        here_cv = compute_tile_cover(self.grid, self.player.col, self.player.row, oob_is_full=settings.COVER_OOB_IS_FULL)
        pieces.append(f"Cover(Here): {cover_to_label(here_cv)}")

        # Plan/hover reachability
        if not self.player.is_moving():
            if self._planned_actions is not None and self._planned_path:
                steps = max(0, len(self._planned_path) - 1)
                pieces.append(f"Planned: {'1A' if self._planned_actions == 1 else '2A Dash'} · {steps} tiles")
            else:
                mx, my = pygame.mouse.get_pos()
                wx, wy = self.camera.screen_to_world(mx, my)
                tc, tr = self.grid.from_px(wx, wy)
                cost = self._range_costs.get((tc, tr))
                actions = self._actions_for_cost(cost)
                if actions is not None:
                    pieces.append(f"Hover: {'1A' if actions == 1 else '2A Dash'} · {cost} tiles")

        # LoF / Flank / Dist vs hovered enemy
        enemy = self._enemy_under_mouse()
        if enemy and (enemy.col, enemy.row) in self._visible:
            shooter = (self.player.col, self.player.row)
            target = (enemy.col, enemy.row)
            has_los = los_clear(self.grid, shooter, target)
            side = facing_side(shooter, target)
            tcv = compute_tile_cover(self.grid, enemy.col, enemy.row, oob_is_full=settings.COVER_OOB_IS_FULL)
            cover_facing = tcv[side]
            flanked = has_los and (cover_facing == "none")
            dist = abs(target[0] - shooter[0]) + abs(target[1] - shooter[1])
            pieces.append(
                f"LoF: {'Yes' if has_los else 'No'} | Flanked: {'Yes' if flanked else 'No'} "
                f"| TargetCoverSide({side}): {'None' if cover_facing=='none' else ('Half' if cover_facing=='half' else 'Full')} "
                f"| Dist: {dist}"
            )

            # Hit% breakdown (compute_hit) + dmg ranges (preview_probabilities)
            bd = compute_hit(self.grid, shooter, target, base_aim=settings.BASE_AIM_PERCENT)
            if not bd.los:
                pieces.append("Shot: Blocked")
            else:
                term_txt = ", ".join([f"{'+' if v>=0 else ''}{v} {k}" for k, v in bd.terms]) if bd.terms else "no mods"
                pieces.append(f"Hit {bd.total}% ({bd.base} base{', ' + term_txt if term_txt else ''})")
                pv = preview_probabilities(self.grid, shooter, target)
                pieces.append(
                    f"Damage Preview: Hit {pv.hit_chance}% | Crit {pv.crit_chance}% | Graze +{pv.graze_band}% "
                    f"| Base {pv.dmg_base_min}-{pv.dmg_base_max} (Graze {pv.dmg_graze_min}-{pv.dmg_graze_max}, Crit {pv.dmg_crit_min}-{pv.dmg_crit_max})"
                )

        # Last shot result
        if self._last_shot_text:
            pieces.append(self._last_shot_text)

        # Render pill
        text = "  |  ".join(pieces)
        pad = 8
        surf_text = self._font.render(text, True, settings.HUD_TEXT_RGB)
        w, h = surf_text.get_size()
        pill = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        tint = settings.OBSTACLE_EDIT_HINT_RGBA if self._obstacle_edit or self._enemy_edit else settings.HUD_BG_RGBA
        pill.fill(tint)
        pill.blit(surf_text, (pad, pad))
        surface.blit(pill, (10, 10))

    def _format_last_shot(self, res) -> str:
        if res.outcome == "blocked":
            return "Last Shot: Blocked"
        return f"Last Shot: {res.outcome.upper()} (roll {res.roll} ≤ hit {res.hit_chance}%{' / crit ' + str(res.crit_chance) + '%' if res.crit_chance else ''}) → {res.damage} dmg"

    # ---- Demo helper ----
    def _seed_demo_obstacles(self) -> None:
        base_c, base_r = self.player.col + 4, self.player.row
        length = 10
        for i in range(length):
            c = base_c + i
            r = base_r + (i % 2)
            if self.grid.in_bounds(c, r) and (c, r) != (self.player.col, self.player.row) and (c, r) not in self._enemies:
                self.grid.blocked.add((c, r))
        if self._selected:
            self._compute_ranges(force=True)
        self._recompute_visibility()
