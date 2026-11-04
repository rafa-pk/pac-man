"""All the drawing: menus, maze, characters and HUD.

Only MLX-like primitives are used: pixels (set_at), images (blit) and text
(string_put). Positions are computed from the size of the window.
"""
import math

import pygame

from src.constants import (BG_COLOR, BOTTOM, CHEAT_ON_COLOR, DIM_COLOR,
                           EYE_COLOR,
                           FACING_ANGLES, FLASH_COLOR, FLASH_TIME, FONT,
                           FRIGHT_COLOR, GAME_OVER_COLOR, GHOST_COLORS,
                           HIGHLIGHT_COLOR, LEFT, LOGO, LOGO_COLOR,
                           LOGO_SPENT_COLOR, MARGIN, MAZE_LEFT, MIN_TILE,
                           MOUTH_ANGLES, NAME_INPUT_MAX, PACGUM_COLOR,
                           PACMAN_COLOR, PAUSE_DIM_ALPHA, PUPIL_COLOR, RIGHT,
                           TEXT_COLOR, TILE, TOP, WALL, WALL_COLOR)
from src.game.scores import Scores
from src.parser import Config

MENU_ITEMS = ("START", "HIGHSCORES", "INSTRUCTIONS", "EXIT")
MENU_HINT = "UP/DOWN or MOUSE: choose - ENTER or CLICK: open - ESC: quit"
CREDITS = ("This project has been created as part of the 42 curriculum "
           "by amaazouz and rvaz-da-")
BACK_LABEL = "< BACK (ESC)"
PAUSE_TITLE = "PAUSED"
PAUSE_ITEMS = ("RESUME", "MAIN MENU")
PAUSE_HINT = "UP/DOWN or MOUSE: choose - ENTER or CLICK: select"
CHEAT_TITLE = "MAKE US PASS!"
CHEAT_HEADER = "CHEATING OPTIONS:"
# The first two are toggles, shown ON or OFF; the others are actions.
CHEAT_ITEMS = ("INVINCIBLE", "FREEZE GHOSTS", "SKIP LEVEL", "RESUME")
# What each panel over a frozen game holds: its title, the labels of its
# rows, a header above its buttons (or None) and its buttons.
PANELS = {
    "pause": (PAUSE_TITLE, ("SCORE", "HIGH SCORE"), None, PAUSE_ITEMS),
    "cheat": (CHEAT_TITLE, ("CURRENT SCORE", "CURRENT LEVEL", "LIVES",
                            "TIME LEFT"), CHEAT_HEADER, CHEAT_ITEMS),
}
GAME_OVER_TITLE = "GAME OVER"
VICTORY_TITLE = "YOU WON"
END_ITEMS = ("SAVE SCORE", "MAIN MENU")
END_HINT = PAUSE_HINT + " - ESC: quit"
NAME_LABEL = "ENTER YOUR NAME"
NAME_RULE = "1 to 10 letters, digits or spaces"
NAME_ERROR = "NAME: 1 TO 10 LETTERS, DIGITS OR SPACES"
RANKS = ("1ST", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH", "8TH", "9TH",
         "10TH")


class GUI:
    """Draws every screen of the game in the window."""

    def __init__(self, screen: pygame.Surface, program: object) -> None:
        """Load the assets, then size the fonts and icons to the window.

        Args:
            screen: The window surface.
            program: The application (kept for the menus).
        """
        self.program = program
        self.logo = pygame.image.load(LOGO).convert_alpha()
        self.resize(screen)

    # ------------------------------------------------------------ layout

    def resize(self, screen: pygame.Surface) -> None:
        """Size the fonts, icons and HUD to the window, at start or later.

        Called again whenever the window changes size (dragged edges,
        green button). The maze keeps the largest cells until set_layout.

        Args:
            screen: The window surface, at its new size.
        """
        self.screen = screen
        self.width, self.height = screen.get_size()
        self.title_font = pygame.font.Font(FONT, max(20, self.height // 16))
        self.menu_font = pygame.font.Font(FONT, max(14, self.height // 26))
        self.hud_font = pygame.font.Font(FONT, max(10, self.height // 40))
        self.small_font = pygame.font.Font(FONT, max(8, self.height // 70))
        icon = max(6, self.height // 50)  # radius of the menu and HUD icons
        self.icon_pacman = self.make_pacman_sprite(icon, 0, 60)
        self.icon_ghosts = [self.make_ghost_sprite(icon, color, 0)
                            for color in GHOST_COLORS.values()]
        self.icon_frightened = self.make_ghost_sprite(icon, FRIGHT_COLOR, 0)
        self.icon_pacgum = self.make_circle_sprite(max(2, icon // 4),
                                                   PACGUM_COLOR)
        self.icon_super = self.make_circle_sprite(max(3, icon // 2),
                                                  PACGUM_COLOR)
        # the HUD panel on the left is at least wide enough for BACK
        self.panel_width = max(MAZE_LEFT, self.back_rect().right + MARGIN)
        self.tile, self.wall = TILE, WALL
        self.offset = (self.panel_width, MARGIN)
        self._make_sprites()
        self._make_panel_layers()

    def _maze_area(self) -> tuple[int, int]:
        """Return the width and height free for the maze, right of the HUD."""
        return (self.width - self.panel_width - MARGIN,
                self.height - 2 * MARGIN)

    def _tile_for(self, width: int, height: int) -> int:
        """Return the cell size of a maze of width x height cells.

        Cells are at most TILE pixels wide: small mazes keep that size and
        big ones shrink until they fit, but never below MIN_TILE (in a tiny
        window the maze overflows instead).
        """
        area_w, area_h = self._maze_area()
        return max(MIN_TILE, min(TILE, area_w // width, area_h // height))

    def maze_frame(self, levels: list[tuple[int, int]]) -> pygame.Rect:
        """Return the frame of the biggest maze of levels, once centred.

        Its width is the widest maze in pixels and its height the tallest
        (the same maze when the levels are square), centred right of the
        HUD. Every maze fits in it: see set_layout.

        Args:
            levels: Size (width, height) of each level, in cells.
        """
        area_w, area_h = self._maze_area()
        widest = max(w * self._tile_for(w, h) for w, h in levels)
        tallest = max(h * self._tile_for(w, h) for w, h in levels)
        return pygame.Rect(self.panel_width + (area_w - widest) // 2,
                           MARGIN + (area_h - tallest) // 2,
                           widest, tallest)

    def set_layout(self, width: int, height: int,
                   frame: pygame.Rect | None = None) -> None:
        """Fit a maze of width x height cells in the window.

        The sprites are redrawn at the new cell size.

        Args:
            width: Width of the maze, in cells.
            height: Height of the maze, in cells.
            frame: Frame of the biggest maze (see maze_frame): the maze
                starts on its left edge, centred on its height, so the
                left edge never moves. Without it, the maze is centred in
                the area right of the HUD.
        """
        self.tile = self._tile_for(width, height)
        self.wall = max(1, WALL * self.tile // TILE)
        if frame is None:
            area_w, area_h = self._maze_area()
            self.offset = (
                self.panel_width + (area_w - width * self.tile) // 2,
                MARGIN + (area_h - height * self.tile) // 2)
        else:
            self.offset = (frame.left, frame.top
                           + (frame.height - height * self.tile) // 2)
        self._make_sprites()

    def _menu_top(self) -> int:
        """Return the y of the centre of the first main-menu entry."""
        return (self._logo_top() + self.logo.get_height()
                + self.height * 16 // 100)

    def _logo_top(self) -> int:
        """Return the y of the top of the logo on the main menu."""
        return self.height * 5 // 100

    def _button_rects(self, labels: tuple[str, ...], centre_x: int,
                      first_y: int) -> list[pygame.Rect]:
        """Return the clickable areas of buttons stacked one under another.

        Args:
            labels: Text of each button, from top to bottom.
            centre_x: x of the centre of every button.
            first_y: y of the centre of the first button.
        """
        step = self.menu_font.get_height() * 22 // 10
        rects = []
        for index, label in enumerate(labels):
            text_w, text_h = self.menu_font.size(label)
            rect = pygame.Rect(0, 0, text_w + 4 * text_h, 2 * text_h)
            rect.center = (centre_x, first_y + index * step)
            rects.append(rect)
        return rects

    def menu_rects(self) -> list[pygame.Rect]:
        """Return the clickable area of each main-menu entry."""
        return self._button_rects(MENU_ITEMS, self.width // 2,
                                  self._menu_top())

    def back_rect(self) -> pygame.Rect:
        """Return the area of the BACK button, bottom left."""
        text_w, text_h = self.hud_font.size(BACK_LABEL)
        return pygame.Rect(MARGIN, self.height - MARGIN - 2 * text_h,
                           text_w + 2 * text_h, 2 * text_h)

    def menu_item_at(self, pos: tuple[int, int]) -> int | None:
        """Return the index of the main-menu entry under pos, or None."""
        for index, rect in enumerate(self.menu_rects()):
            if rect.collidepoint(pos):
                return index
        return None

    def back_button_hit(self, pos: tuple[int, int]) -> bool:
        """Tell whether pos is on the BACK button."""
        return self.back_rect().collidepoint(pos)

    def _panel_rows(self, kind: str) -> tuple[int, int, int, int, int]:
        """Return where the parts of a panel go, from its top.

        Args:
            kind: The panel, a key of PANELS ("pause" or "cheat").

        Returns:
            The y of the first row, of the header, of the centre of the
            first button and of the hint, and the height of the panel.
        """
        _, rows, header, items = PANELS[kind]
        pad = self.title_font.get_height()
        hud_h = self.hud_font.get_height()
        menu_h = self.menu_font.get_height()
        rows_y = pad * 3  # margin, title, gap
        header_y = rows_y + len(rows) * hud_h * 2
        buttons_y = header_y + menu_h * 2 + (hud_h if header else 0)
        hint_y = (buttons_y + (len(items) - 1) * (menu_h * 22 // 10)
                  + menu_h * 2)
        # the taller cheat panel has a smaller bottom margin, so it still
        # fits a 720 px high screen
        bottom = (2 * pad if kind == "pause"
                  else self.small_font.get_height() + pad)
        return rows_y, header_y, buttons_y, hint_y, hint_y + bottom

    def panel_rect(self, kind: str) -> pygame.Rect:
        """Return the area of a panel, centred in the window.

        It is wide enough for every line, scores of 12 digits included,
        and for the ON/OFF of the cheat toggles beside their buttons.
        """
        title, rows, header, items = PANELS[kind]
        pad = self.title_font.get_height()
        icon_w = self.icon_pacman.get_width()
        state_w = self.menu_font.size("OFF")[0] if kind == "cheat" else 0
        width = max(self.title_font.size(title)[0],
                    *(self.hud_font.size(label + "  " + "9" * 12)[0]
                      for label in rows),
                    self.hud_font.size(header or "")[0],
                    self.small_font.size(PAUSE_HINT)[0],
                    *(self.menu_font.size(label)[0] + 6 * icon_w
                      + 2 * state_w for label in items))
        rect = pygame.Rect(0, 0, width + 2 * pad, self._panel_rows(kind)[4])
        rect.center = (self.width // 2, self.height // 2)
        return rect

    def panel_rects(self, kind: str) -> list[pygame.Rect]:
        """Return the clickable area of each button of a panel."""
        panel = self.panel_rect(kind)
        return self._button_rects(PANELS[kind][3], panel.centerx,
                                  panel.top + self._panel_rows(kind)[2])

    def panel_item_at(self, kind: str, pos: tuple[int, int]) -> int | None:
        """Return the index of the panel button under pos, or None."""
        for index, rect in enumerate(self.panel_rects(kind)):
            if rect.collidepoint(pos):
                return index
        return None

    def _end_rows(self) -> tuple[int, int, int, int, int, int]:
        """Return where the parts of the end screen go, under the logo.

        Returns:
            The y of the title, of the final score, of the name label, of
            the top of the name box, of the rule (or error) line, and of
            the centre of the first button.
        """
        hud_h = self.hud_font.get_height()
        title_y = self._logo_top() + self.logo.get_height() + hud_h
        score_y = title_y + self.title_font.get_height() * 3 // 2
        label_y = score_y + hud_h * 2
        box_y = label_y + hud_h * 3 // 2
        rule_y = box_y + hud_h * 2 + hud_h // 2  # under the box
        buttons_y = (rule_y + self.small_font.get_height()
                     + self.menu_font.get_height() * 3 // 2)
        return title_y, score_y, label_y, box_y, rule_y, buttons_y

    def name_box_rect(self) -> pygame.Rect:
        """Return the frame of the name input, wide for NAME_INPUT_MAX."""
        text_w, text_h = self.hud_font.size("W" * (NAME_INPUT_MAX + 1))
        rect = pygame.Rect(0, self._end_rows()[3], text_w + 2 * text_h,
                           2 * text_h)
        rect.centerx = self.width // 2
        return rect

    def end_rects(self) -> list[pygame.Rect]:
        """Return the clickable area of each end-screen button."""
        return self._button_rects(END_ITEMS, self.width // 2,
                                  self._end_rows()[5])

    def end_item_at(self, pos: tuple[int, int]) -> int | None:
        """Return the index of the end-screen button under pos, or None."""
        for index, rect in enumerate(self.end_rects()):
            if rect.collidepoint(pos):
                return index
        return None

    # ------------------------------------------------------------ sprites

    def _make_sprites(self) -> None:
        """Draw the pacgum, Pac-Man and ghost sprites for the cell size."""
        scale = self.tile / TILE
        self.pacgum_sprite = self.make_circle_sprite(
            max(1, round(3 * scale)), PACGUM_COLOR)
        self.super_sprite = self.make_circle_sprite(
            max(2, round(6 * scale)), PACGUM_COLOR)
        # the inside of a "42" cell, between its walls
        inner = self.tile - 2 * self.wall
        self.logo_sprite = pygame.Surface((inner, inner))
        self.draw_rect(self.logo_sprite, LOGO_COLOR, 0, 0, inner, inner)
        radius = max(3, round((TILE // 2 - 4) * scale))
        self.pacman_frames = {
            (facing, frame): self.make_pacman_sprite(radius, angle, mouth)
            for facing, angle in FACING_ANGLES.items()
            for frame, mouth in enumerate(MOUTH_ANGLES)
        }
        ghost_colors = {**GHOST_COLORS, "frightened": FRIGHT_COLOR,
                        "flashing": FLASH_COLOR}
        self.ghost_frames = {
            (name, facing): self.make_ghost_sprite(radius, color, angle)
            for name, color in ghost_colors.items()
            for facing, angle in FACING_ANGLES.items()
        }
        for facing, angle in FACING_ANGLES.items():
            self.ghost_frames[("eyes", facing)] = self.make_eyes_sprite(
                radius, angle)

    def _make_panel_layers(self) -> None:
        """Make the dark layer and the background of each panel, once.

        They are filled when the window gets its size, so a paused frame
        only blits them instead of painting them pixel by pixel.
        """
        self.panel_dim = pygame.Surface((self.width, self.height),
                                        pygame.SRCALPHA)
        self.panel_dim.fill((*BG_COLOR, PAUSE_DIM_ALPHA))
        self.panel_backgrounds = {}
        for kind in PANELS:
            background = pygame.Surface(self.panel_rect(kind).size)
            background.fill(BG_COLOR)
            self.panel_backgrounds[kind] = background

    @staticmethod
    def fill_circle(surface: pygame.Surface, color: tuple[int, int, int],
                    cx: int, cy: int, radius: int) -> None:
        """Paint a disc on surface, pixel by pixel."""
        r2 = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= r2:
                    surface.set_at((cx + dx, cy + dy), color)

    def make_circle_sprite(self, radius: int,
                           color: tuple[int, int, int]) -> pygame.Surface:
        """Return a transparent sprite holding a disc."""
        size = radius * 2 + 1
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        self.fill_circle(sprite, color, radius, radius, radius)
        return sprite

    @staticmethod
    def make_pacman_sprite(radius: int, facing: float,
                           mouth: float) -> pygame.Surface:
        """Draw Pac-Man pixel by pixel: a disc minus the mouth wedge.

        Args:
            radius: Radius in pixels.
            facing: Direction of the mouth in degrees (0 = right, 90 = down).
            mouth: Opening of the mouth in degrees (0 = closed).
        """
        size = radius * 2 + 1
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy > radius * radius:
                    continue
                angle = math.degrees(math.atan2(dy, dx))
                if abs((angle - facing + 180) % 360 - 180) < mouth / 2:
                    continue  # inside the mouth
                sprite.set_at((radius + dx, radius + dy), PACMAN_COLOR)
        return sprite

    @staticmethod
    def make_ghost_sprite(radius: int, color: tuple[int, int, int],
                          facing: float) -> pygame.Surface:
        """Draw a ghost pixel by pixel: round head, wavy skirt, eyes.

        Args:
            radius: Half the width of the sprite, in pixels.
            color: Color of the body.
            facing: Where the eyes look, in degrees (0 = right, 90 = down).
        """
        size = radius * 2 + 1
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        skirt = max(2, radius // 3)  # height of the wavy bottom
        wave = size / 3  # width of one of the 3 waves
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dy < 0:  # round head
                    inside = dx * dx + dy * dy <= radius * radius
                elif dy <= radius - skirt:  # straight body
                    inside = True
                else:  # waves pointing down
                    centre = ((dx + radius) // wave + 0.5) * wave - radius
                    inside = (abs(dx - centre) * skirt
                              <= (radius - dy) * wave / 2)
                if inside:
                    sprite.set_at((radius + dx, radius + dy), color)
        GUI.draw_eyes(sprite, radius, facing)
        return sprite

    @staticmethod
    def make_eyes_sprite(radius: int, facing: float) -> pygame.Surface:
        """Draw only the eyes of a ghost: what is left once it is eaten."""
        size = radius * 2 + 1
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        GUI.draw_eyes(sprite, radius, facing)
        return sprite

    @staticmethod
    def draw_eyes(sprite: pygame.Surface, radius: int,
                  facing: float) -> None:
        """Paint the two eyes of a ghost, looking towards facing (degrees)."""
        look_x = round(math.cos(math.radians(facing)) * radius / 8)
        look_y = round(math.sin(math.radians(facing)) * radius / 8)
        eye_y = radius - round(radius * 0.2)
        for side in (-1, 1):
            eye_x = radius + side * round(radius * 0.4)
            GUI.fill_circle(sprite, EYE_COLOR, eye_x, eye_y,
                            max(1, round(radius * 0.3)))
            GUI.fill_circle(sprite, PUPIL_COLOR, eye_x + look_x,
                            eye_y + look_y, max(1, round(radius * 0.15)))

    # ------------------------------------------------------------ primitives

    def string_put(self, x: int, y: int, color: tuple[int, int, int],
                   font: pygame.font.Font, text: str) -> None:
        """Draw text with its top-left corner at (x, y)."""
        string = font.render(text, False, color)
        self.screen.blit(string, (x, y))

    def _text(self, font: pygame.font.Font, text: str,
              color: tuple[int, int, int], x: int, y: int,
              align: str = "left") -> None:
        """Draw text with its top at y; x is its left, centre or right."""
        if align == "center":
            x -= font.size(text)[0] // 2
        elif align == "right":
            x -= font.size(text)[0]
        self.string_put(x, y, color, font, text)

    def draw_rect(self, surface: pygame.Surface, color: tuple[int, int, int],
                  x: int, y: int, w: int, h: int) -> None:
        """Paint a filled rectangle on surface, pixel by pixel."""
        for py in range(y, y + h):
            for px in range(x, x + w):
                surface.set_at((px, py), color)

    def _frame(self, rect: pygame.Rect, color: tuple[int, int, int],
               thickness: int = 2) -> None:
        """Paint the outline of rect on the screen."""
        x, y, w, h = rect
        sides = ((x, y, w, thickness), (x, y + h - thickness, w, thickness),
                 (x, y, thickness, h), (x + w - thickness, y, thickness, h))
        for side in sides:
            self.draw_rect(self.screen, color, *side)

    def _title(self, text: str) -> int:
        """Draw a screen title at the top and return the y below it."""
        top = self.height * 7 // 100
        self._text(self.title_font, text, HIGHLIGHT_COLOR, self.width // 2,
                   top, "center")
        return top + self.title_font.get_height() * 2

    def _draw_back_button(self) -> None:
        """Draw the BACK button, lit when the mouse is over it."""
        rect = self.back_rect()
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        self._frame(rect, HIGHLIGHT_COLOR if hovered else WALL_COLOR)
        text_h = self.hud_font.get_height()
        self._text(self.hud_font, BACK_LABEL,
                   HIGHLIGHT_COLOR if hovered else TEXT_COLOR,
                   rect.centerx, rect.centery - text_h // 2, "center")

    # ------------------------------------------------------------ menus

    def draw_main_menu(self, menu_index: int) -> None:
        """Draw the logo, the parade of characters and the menu entries."""
        self.screen.fill(BG_COLOR)
        self.screen.blit(self.logo, ((self.width - self.logo.get_width())
                                     // 2, self._logo_top()))
        self._draw_parade(self._logo_top() + self.logo.get_height()
                          + self.height * 5 // 100)
        self._draw_buttons(MENU_ITEMS, self.menu_rects(), menu_index)
        small_h = self.small_font.get_height()
        self._text(self.small_font, MENU_HINT, DIM_COLOR, self.width // 2,
                   self.height - MARGIN - small_h * 4, "center")
        self._text(self.small_font, "© " + CREDITS, TEXT_COLOR,
                   self.width // 2, self.height - MARGIN - small_h, "center")

    def _draw_buttons(self, labels: tuple[str, ...], rects: list[pygame.Rect],
                      selected: int) -> None:
        """Draw menu entries; the selected one is lit, Pac-Man beside it."""
        for index, (label, rect) in enumerate(zip(labels, rects)):
            text_w, text_h = self.menu_font.size(label)
            self._text(self.menu_font, label,
                       HIGHLIGHT_COLOR if index == selected else TEXT_COLOR,
                       rect.centerx, rect.centery - text_h // 2, "center")
            if index == selected:
                icon = self.icon_pacman
                self.screen.blit(icon, (rect.centerx - text_w // 2
                                        - icon.get_width() * 2,
                                        rect.centery - icon.get_height() // 2))

    def _draw_parade(self, centre_y: int) -> None:
        """Draw the four ghosts chasing Pac-Man, who chases three pacgums."""
        icons = [*self.icon_ghosts, self.icon_pacman]
        step = self.icon_pacman.get_width() * 3 // 2
        x = self.width // 2 - (len(icons) + 2) * step // 2
        for icon in icons:
            self.screen.blit(icon, (x, centre_y - icon.get_height() // 2))
            x += step
        for _ in range(3):
            dot = self.icon_pacgum
            self.screen.blit(dot, (x + step // 3, centre_y
                                   - dot.get_height() // 2))
            x += step * 2 // 3

    def draw_highscores(self, scores: Scores) -> None:
        """Draw the top 10, or a message when there is no score yet."""
        self.screen.fill(BG_COLOR)
        top = self._title("HIGH SCORES")
        entries = scores.fetch_entries()
        if not entries:
            self._text(self.menu_font, "NO SCORES YET", TEXT_COLOR,
                       self.width // 2, self.height // 2, "center")
        row_h = self.hud_font.get_height() * 2
        table_w = self.hud_font.size("10TH  " + "W" * 10 + "  " + "9" * 12)[0]
        left = (self.width - table_w) // 2
        name_x = left + self.hud_font.size("10TH  ")[0]
        for rank, entry in zip(RANKS, entries):
            self._text(self.hud_font, rank, HIGHLIGHT_COLOR, left, top)
            self._text(self.hud_font, str(entry.get("name", "?"))[:10],
                       TEXT_COLOR, name_x, top)
            self._text(self.hud_font, str(entry.get("score", "")),
                       TEXT_COLOR, left + table_w, top, "right")
            top += row_h
        self._draw_back_button()

    def draw_instructions(self, config: Config) -> None:
        """Draw the controls and the rules, with the points of the config."""
        self.screen.fill(BG_COLOR)
        top = self._title("INSTRUCTIONS")
        rows: list[tuple[pygame.Surface | None, str, str]] = [
            (None, "CONTROLS", ""),
            (None, "ARROWS / WASD (ZQSD)", "move Pac-Man"),
            (None, "ESC", "back to the menu"),
            (None, "SPACE", "pause the game"),
            (None, "C", "cheat mode"),
            (None, "MOUSE", "choose and click in the menus"),
            (None, "", ""),
            (None, "RULES", ""),
            (self.icon_pacgum, "PACGUM", f"{config.points_per_pacgum} pts"),
            (self.icon_super, "SUPER-PACGUM",
             f"{config.points_per_super_pacgum} pts"),
            (self.icon_ghosts[0], "GHOST", "costs a life"),
            (self.icon_frightened, "BLUE GHOST",
             f"{config.points_per_ghost} pts"),
            (None, "", ""),
            (None, "Eat every pacgum to clear the level.", ""),
            (None, f"{len(config.levels)} levels, {config.lives} lives.", ""),
        ]
        row_h = self.hud_font.get_height() * 2
        key_w = max(self.hud_font.size(key)[0] for _, key, text in rows
                    if text)
        text_w = max(self.hud_font.size(text)[0] for _, _, text in rows)
        gap = self.hud_font.size("   ")[0]
        left = (self.width - key_w - gap - text_w) // 2
        middle = left + key_w + gap
        for icon, key, text in rows:
            heading = key in ("CONTROLS", "RULES")
            if icon is not None:
                self.screen.blit(icon, (left - icon.get_width() - gap // 2,
                                        top + (self.hud_font.get_height()
                                               - icon.get_height()) // 2))
            self._text(self.hud_font, key,
                       HIGHLIGHT_COLOR if heading else TEXT_COLOR, left, top)
            self._text(self.hud_font, text, TEXT_COLOR, middle, top)
            top += row_h
        self._draw_back_button()

    def draw_game_end(self, won: bool, score: int, name: str, selected: int,
                      error: bool = False) -> None:
        """Draw the victory or game-over screen, with the name input.

        Args:
            won: True for the victory screen, False for game over.
            score: Final score of the game.
            name: Text typed so far in the name box.
            selected: Index of the lit button in END_ITEMS.
            error: Show the name rule as an error, in red.
        """
        self.screen.fill(BG_COLOR)
        centre = self.width // 2
        self.screen.blit(self.logo, (centre - self.logo.get_width() // 2,
                                     self._logo_top()))
        title_y, score_y, label_y, _, rule_y, _ = self._end_rows()
        if won:
            self._text(self.title_font, VICTORY_TITLE, HIGHLIGHT_COLOR,
                       centre, title_y, "center")
        else:
            self._text(self.title_font, GAME_OVER_TITLE, GAME_OVER_COLOR,
                       centre, title_y, "center")
        # "FINAL SCORE  1234": the label lit, the whole line centred
        label = "FINAL SCORE  "
        left = centre - self.hud_font.size(label + str(score))[0] // 2
        self._text(self.hud_font, label, HIGHLIGHT_COLOR, left, score_y)
        self._text(self.hud_font, str(score), TEXT_COLOR,
                   left + self.hud_font.size(label)[0], score_y)
        self._text(self.hud_font, NAME_LABEL, HIGHLIGHT_COLOR, centre,
                   label_y, "center")
        box = self.name_box_rect()
        self._frame(box, WALL_COLOR)
        cursor = "_" if pygame.time.get_ticks() // 500 % 2 == 0 else ""
        text_h = self.hud_font.get_height()
        self._text(self.hud_font, name + cursor, TEXT_COLOR,
                   box.left + text_h, box.centery - text_h // 2)
        if error:
            self._text(self.small_font, NAME_ERROR, GAME_OVER_COLOR, centre,
                       rule_y, "center")
        else:
            self._text(self.small_font, NAME_RULE, DIM_COLOR, centre, rule_y,
                       "center")
        self._draw_buttons(END_ITEMS, self.end_rects(), selected)
        small_h = self.small_font.get_height()
        self._text(self.small_font, END_HINT, DIM_COLOR, centre,
                   self.height - MARGIN - small_h * 2, "center")

    # ------------------------------------------------------------ game

    def create_maze_surface(self, maze: list[list[int]]) -> pygame.Surface:
        """Draw the walls of maze once, on a surface blitted every frame.

        The "42" cells are painted as spent here: every frame, draw_logo
        covers the ones still lit, so the spent ones show through.
        """
        tile, wall = self.tile, self.wall
        surface = pygame.Surface((len(maze[0]) * tile, len(maze) * tile))
        surface.fill(BG_COLOR)
        for y, row in enumerate(maze):
            for x, cell in enumerate(row):
                px, py = x * tile, y * tile
                if cell == 15:  # a "42" cell: fill it between its walls
                    self.draw_rect(surface, LOGO_SPENT_COLOR, px + wall,
                                   py + wall, tile - 2 * wall,
                                   tile - 2 * wall)
                if cell & TOP:
                    self.draw_rect(surface, WALL_COLOR, px, py, tile, wall)
                if cell & RIGHT:
                    self.draw_rect(surface, WALL_COLOR, px + tile - wall, py,
                                   wall, tile)
                if cell & BOTTOM:
                    self.draw_rect(surface, WALL_COLOR, px, py + tile - wall,
                                   tile, wall)
                if cell & LEFT:
                    self.draw_rect(surface, WALL_COLOR, px, py, wall, tile)
        return surface

    def draw_pacgums(self, available_pg: set[tuple[int, int]],
                     available_spg: set[tuple[int, int]]) -> None:
        """Draw the pacgums and super-pacgums left in the level."""
        for x, y in available_pg:
            self._blit_on_cell(self.pacgum_sprite, (x, y))
        for x, y in available_spg:
            self._blit_on_cell(self.super_sprite, (x, y))

    def draw_maze(self, maze_surface: pygame.Surface) -> None:
        """Clear the screen, then draw the maze and the BACK button."""
        self.screen.fill(BG_COLOR)
        self.screen.blit(maze_surface, self.offset)
        self._draw_back_button()

    def draw_logo(self, cells: list[tuple[int, int]]) -> None:
        """Fill these cells of the "42", the others stay empty."""
        ox, oy = self.offset
        for x, y in cells:
            px = ox + x * self.tile + self.wall
            py = oy + y * self.tile + self.wall
            self.screen.blit(self.logo_sprite, (px, py))

    def draw_player(self, pos: tuple[float, float], facing: str,
                    opening: float) -> None:
        """Draw Pac-Man, his mouth open by opening (0 to 1)."""
        frame = round(opening * (len(MOUTH_ANGLES) - 1))
        self._blit_on_cell(self.pacman_frames[(facing, frame)], pos)

    @staticmethod
    def ghost_look(name: str, fright_time: float,
                   eaten: bool = False) -> str:
        """Return which frames to draw: own, blue, flashing or eyes only.

        An edible ghost is blue, and flashes white 4 times per second
        during its last FLASH_TIME seconds. An eaten one is only eyes.
        """
        if eaten:
            return "eyes"
        if fright_time <= 0:
            return name
        if fright_time < FLASH_TIME and int(fright_time * 8) % 2 == 1:
            return "flashing"
        return "frightened"

    def draw_ghost(self, pos: tuple[float, float], name: str, facing: str,
                   fright_time: float = 0.0, eaten: bool = False) -> None:
        """Draw a ghost, its eyes looking where it goes."""
        look = self.ghost_look(name, fright_time, eaten)
        self._blit_on_cell(self.ghost_frames[(look, facing)], pos)

    def _blit_on_cell(self, sprite: pygame.Surface,
                      pos: tuple[float, float]) -> None:
        """Draw sprite centred on pos, given in cells (can be between two)."""
        ox, oy = self.offset
        width, height = sprite.get_size()
        px = ox + pos[0] * self.tile + (self.tile - width) // 2
        py = oy + pos[1] * self.tile + (self.tile - height) // 2
        self.screen.blit(sprite, (px, py))

    @staticmethod
    def format_time(seconds: float) -> str:
        """Return seconds as m:ss, rounded up: 90 -> "1:30", 0.2 -> "0:01"."""
        whole = max(0, math.ceil(seconds))
        return f"{whole // 60}:{whole % 60:02d}"

    def draw_hud(self, score: int, level: int, lives: int,
                 time_left: float) -> None:
        """Draw the score, level, time and lives left of the maze."""
        y = MARGIN * 2
        for label, value in (("SCORE", str(score)), ("LEVEL", str(level)),
                             ("TIME", self.format_time(time_left))):
            self._text(self.hud_font, label, HIGHLIGHT_COLOR, MARGIN, y)
            y += self.hud_font.get_height() * 3 // 2
            self._text(self.menu_font, value, TEXT_COLOR, MARGIN, y)
            y += self.menu_font.get_height() * 2
        self._text(self.hud_font, "LIVES", HIGHLIGHT_COLOR, MARGIN, y)
        y += self.hud_font.get_height() * 3 // 2
        icon = self.icon_pacman
        step = icon.get_width() * 3 // 2
        per_row = max(1, (self.panel_width - 2 * MARGIN) // step)
        for life in range(lives):
            self.screen.blit(icon, (MARGIN + life % per_row * step,
                                    y + life // per_row * step))

    def _draw_panel(self, kind: str, selected: int,
                    values: list[str]) -> pygame.Rect:
        """Draw a panel over the frozen game, already on screen.

        Args:
            kind: The panel, a key of PANELS ("pause" or "cheat").
            selected: Index of the lit button.
            values: Value shown on each row, in the order of PANELS.

        Returns:
            The area of the panel.
        """
        title, rows, header, items = PANELS[kind]
        self.screen.blit(self.panel_dim, (0, 0))
        panel = self.panel_rect(kind)
        self.screen.blit(self.panel_backgrounds[kind], panel.topleft)
        self._frame(panel, WALL_COLOR)
        pad = self.title_font.get_height()
        rows_y, header_y, _, hint_y, _ = self._panel_rows(kind)
        self._text(self.title_font, title, HIGHLIGHT_COLOR,
                   panel.centerx, panel.top + pad, "center")
        y = panel.top + rows_y
        for label, value in zip(rows, values):
            self._text(self.hud_font, label, HIGHLIGHT_COLOR,
                       panel.left + pad, y)
            self._text(self.hud_font, value, TEXT_COLOR,
                       panel.right - pad, y, "right")
            y += self.hud_font.get_height() * 2
        if header:
            self._text(self.hud_font, header, HIGHLIGHT_COLOR,
                       panel.left + pad, panel.top + header_y)
        self._draw_buttons(items, self.panel_rects(kind), selected)
        self._text(self.small_font, PAUSE_HINT, DIM_COLOR, panel.centerx,
                   panel.top + hint_y, "center")
        return panel

    def draw_pause(self, selected: int, score: int, high_score: int) -> None:
        """Draw the pause menu over the frozen game, already on screen.

        Args:
            selected: Index of the lit button in PAUSE_ITEMS.
            score: Score of the game being played.
            high_score: Best score saved in the leaderboard.
        """
        self._draw_panel("pause", selected, [str(score), str(high_score)])

    def draw_cheat(self, selected: int, score: int, level: int, lives: int,
                   time_left: float, toggles: tuple[bool, ...]) -> None:
        """Draw the cheat menu over the frozen game, already on screen.

        Args:
            selected: Index of the lit button in CHEAT_ITEMS.
            score: Score of the game being played.
            level: Number of the level, 1 for the first.
            lives: Lives left.
            time_left: Seconds left in the level.
            toggles: State of the first buttons (invincible, frozen
                ghosts), each shown beside its button: ON or OFF.
        """
        panel = self._draw_panel("cheat", selected,
                                 [str(score), str(level), str(lives),
                                  self.format_time(time_left)])
        right = panel.right - self.title_font.get_height()
        text_h = self.menu_font.get_height()
        for rect, on in zip(self.panel_rects("cheat"), toggles):
            self._text(self.menu_font, "ON" if on else "OFF",
                       CHEAT_ON_COLOR if on else GAME_OVER_COLOR, right,
                       rect.centery - text_h // 2, "right")
