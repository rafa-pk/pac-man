"""Tests for src/gui.py: the Pac-Man sprite and the maze layout."""
from pathlib import Path

import pygame
import pytest

from src.constants import (BG_COLOR, CHEAT_ON_COLOR, EYE_COLOR,
                           GAME_OVER_COLOR, GHOST_COLORS, HIGHLIGHT_COLOR,
                           LOGO_COLOR, LOGO_SPENT_COLOR, MARGIN, MAZE_LEFT,
                           MIN_TILE, PUPIL_COLOR)
from src.game.scores import Scores
from src.gui import GUI
from src.parser import Config

ROOT = Path(__file__).resolve().parent.parent

RADIUS = 20


def is_drawn(facing: float, mouth: float, dx: int, dy: int) -> bool:
    """Tell whether the pixel at (dx, dy) from the centre is painted."""
    sprite = GUI.make_pacman_sprite(RADIUS, facing, mouth)
    return sprite.get_at((RADIUS + dx, RADIUS + dy)).a == 255


def test_closed_mouth_is_a_full_disc() -> None:
    """With the mouth closed, both sides of the disc are painted."""
    assert is_drawn(0, 0, 15, 0)
    assert is_drawn(0, 0, -15, 0)


def test_open_mouth_points_where_pacman_faces() -> None:
    """The mouth is a transparent wedge on the facing side only."""
    assert not is_drawn(0, 90, 15, 0)  # facing right: hole on the right
    assert is_drawn(0, 90, -15, 0)
    assert not is_drawn(270, 90, 0, -15)  # facing up: hole on top
    assert is_drawn(270, 90, 0, 15)


def test_corners_stay_transparent() -> None:
    """Pixels outside the disc are never painted."""
    assert not is_drawn(0, 0, -RADIUS, -RADIUS)


@pytest.fixture
def gui(monkeypatch: pytest.MonkeyPatch) -> GUI:
    """The GUI on a 1400 x 800 screen, without a window."""
    monkeypatch.chdir(ROOT)  # the assets are loaded with relative paths
    pygame.init()
    return GUI(pygame.display.set_mode((1400, 800)), None)


@pytest.mark.parametrize("size, tile", [(5, 50), (15, 50), (20, 37),
                                        (42, 17), (50, 15)])
def test_cell_size_fits_the_window(gui: GUI, size: int, tile: int) -> None:
    """Small mazes keep 50 px cells; bigger ones get smaller cells."""
    gui.set_layout(size, size)
    assert gui.tile == tile


def test_every_default_level_fits_on_screen(gui: GUI) -> None:
    """Each default level is fully visible, right of the HUD."""
    for level in Config().levels:
        gui.set_layout(level.width, level.height)
        x, y = gui.offset
        assert x >= MAZE_LEFT and y >= 0
        assert x + level.width * gui.tile <= 1400
        assert y + level.height * gui.tile <= 800


@pytest.mark.parametrize("size", [(1920, 1080), (1280, 720), (1400, 800)])
def test_resize_fits_the_new_window(gui: GUI,
                                    size: tuple[int, int]) -> None:
    """After a change of size, the levels and buttons fit the new window."""
    gui.resize(pygame.display.set_mode(size))
    assert (gui.width, gui.height) == size
    for level in Config().levels:
        gui.set_layout(level.width, level.height)
        x, y = gui.offset
        assert x >= gui.panel_width and y >= 0
        assert x + level.width * gui.tile <= size[0]
        assert y + level.height * gui.tile <= size[1]
    for rect in gui.menu_rects() + [gui.back_rect()]:
        assert 0 <= rect.top and rect.bottom <= size[1]


def test_a_tiny_window_does_not_crash(gui: GUI) -> None:
    """Dragged very small, the cells stop at MIN_TILE and still draw."""
    gui.resize(pygame.display.set_mode((200, 150)))
    gui.set_layout(42, 42)
    assert gui.tile == MIN_TILE
    gui.create_maze_surface([[13, 15, 7]])
    gui.draw_logo([(1, 0)])


def test_pacman_stays_smaller_than_a_cell(gui: GUI) -> None:
    """The sprites are redrawn at the size of the new cells."""
    for size in (15, 42, 50):
        gui.set_layout(size, size)
        assert gui.pacman_frames[("right", 0)].get_width() < gui.tile


def test_logo_sprite_fills_a_cell_inside_its_walls(gui: GUI) -> None:
    """A lit "42" cell is cream, between the walls of the cell."""
    for size in (15, 42):
        gui.set_layout(size, size)
        inner = gui.tile - 2 * gui.wall
        assert gui.logo_sprite.get_size() == (inner, inner)
        assert tuple(gui.logo_sprite.get_at((0, 0)))[:3] == LOGO_COLOR


def test_spent_42_cells_differ_from_the_corridors(gui: GUI) -> None:
    """Under the lit cells, the "42" is painted as spent, not left empty."""
    gui.set_layout(3, 1)
    surface = gui.create_maze_surface([[13, 15, 7]])  # middle cell closed
    centre = gui.tile // 2
    assert tuple(surface.get_at((gui.tile + centre, centre)))[:3] \
        == LOGO_SPENT_COLOR
    assert tuple(surface.get_at((centre, centre)))[:3] == BG_COLOR


@pytest.mark.parametrize("seconds, shown", [
    (90, "1:30"), (89.2, "1:30"), (59.5, "1:00"), (9, "0:09"),
    (0.2, "0:01"), (0, "0:00"), (600, "10:00")])
def test_time_is_shown_as_minutes_and_seconds(seconds: float,
                                              shown: str) -> None:
    """The HUD shows the time left as m:ss, rounded up."""
    assert GUI.format_time(seconds) == shown


def test_ghost_sprite_shape() -> None:
    """Round head, body color in the middle, transparent corners."""
    red = GHOST_COLORS["blinky"]
    sprite = GUI.make_ghost_sprite(RADIUS, red, 0)
    assert tuple(sprite.get_at((RADIUS, 1)))[:3] == red
    assert tuple(sprite.get_at((RADIUS, RADIUS)))[:3] == red
    assert sprite.get_at((0, 0)).a == 0


def pupils_x(facing: float) -> float:
    """Return the mean x of the pupil pixels of a ghost sprite."""
    sprite = GUI.make_ghost_sprite(RADIUS, GHOST_COLORS["blinky"], facing)
    size = sprite.get_width()
    xs = [x for x in range(size) for y in range(size)
          if tuple(sprite.get_at((x, y)))[:3] == PUPIL_COLOR]
    return sum(xs) / len(xs)


def test_ghost_eyes_look_where_it_goes() -> None:
    """The pupils move to the right or to the left of the eyes."""
    assert pupils_x(0) > RADIUS > pupils_x(180)


@pytest.mark.parametrize("fright_time, look", [
    (0.0, "pinky"), (5.0, "frightened"), (1.9, "flashing"),
    (1.8, "frightened")])
def test_edible_ghosts_are_blue_then_flash(fright_time: float,
                                           look: str) -> None:
    """Blue while edible, flashing white in the last FLASH_TIME seconds."""
    assert GUI.ghost_look("pinky", fright_time) == look


def test_eaten_ghosts_are_only_eyes() -> None:
    """An eaten ghost shows its eyes, without a body."""
    assert GUI.ghost_look("pinky", 3.0, eaten=True) == "eyes"
    sprite = GUI.make_eyes_sprite(RADIUS, 0)
    assert sprite.get_at((RADIUS, RADIUS)).a == 0  # no body
    colors = {tuple(sprite.get_at((x, y)))[:3]
              for x in range(sprite.get_width())
              for y in range(sprite.get_height())}
    assert EYE_COLOR in colors and PUPIL_COLOR in colors


@pytest.mark.parametrize("size", [(1280, 720), (1440, 900), (1920, 1080)])
def test_every_screen_draws_on_usual_screens(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        size: tuple[int, int]) -> None:
    """Menus, scores, instructions and HUD draw on usual screen sizes."""
    monkeypatch.chdir(ROOT)
    pygame.init()
    gui = GUI(pygame.display.set_mode(size), None)
    gui.draw_main_menu(1)
    gui.draw_highscores(Scores(str(tmp_path / "scores.json")))
    gui.draw_instructions(Config())
    gui.draw_hud(1234, 2, 9, 87.2)
    for rect in gui.menu_rects() + [gui.back_rect()]:
        assert 0 <= rect.top and rect.bottom <= size[1]


def test_menu_entries_are_clickable(gui: GUI) -> None:
    """Each entry answers to a click on its centre, and only there."""
    for index, rect in enumerate(gui.menu_rects()):
        assert gui.menu_item_at(rect.center) == index
    assert gui.menu_item_at((0, 0)) is None


def test_back_button_is_clickable(gui: GUI) -> None:
    """The BACK button, bottom left, answers to a click on it."""
    rect = gui.back_rect()
    assert gui.back_button_hit(rect.center)
    assert not gui.back_button_hit((gui.width - 1, 0))
    assert rect.right < gui.width // 3


def test_pause_buttons_are_clickable(gui: GUI) -> None:
    """Each pause button answers to a click on its centre, and only there."""
    for index, rect in enumerate(gui.panel_rects("pause")):
        assert gui.panel_item_at("pause", rect.center) == index
    assert gui.panel_item_at("pause", (0, 0)) is None


@pytest.mark.parametrize("size", [(1280, 720), (1440, 900), (1920, 1080)])
def test_pause_menu_fits_usual_screens(gui: GUI,
                                       size: tuple[int, int]) -> None:
    """The panel is centred in the window and holds its two buttons."""
    gui.resize(pygame.display.set_mode(size))
    panel = gui.panel_rect("pause")
    assert panel.center == (size[0] // 2, size[1] // 2)
    assert gui.screen.get_rect().contains(panel)
    assert gui.panel_dim.get_size() == size
    assert gui.panel_backgrounds["pause"].get_size() == panel.size
    for rect in gui.panel_rects("pause"):
        assert panel.contains(rect)
    gui.draw_pause(1, 1234, 92482298420)


def title_colors(gui: GUI, won: bool) -> set[tuple[int, ...]]:
    """Return the colors drawn on the title line of the end screen."""
    gui.draw_game_end(won, 1234, "rafa", 0)
    title_y = gui._end_rows()[0]
    return {tuple(gui.screen.get_at((x, title_y + y)))[:3]
            for x in range(gui.width)
            for y in range(gui.title_font.get_height())}


def test_end_titles_and_their_colors(gui: GUI) -> None:
    """GAME OVER is red; YOU WON has the amber of the other titles."""
    assert GAME_OVER_COLOR in title_colors(gui, won=False)
    assert HIGHLIGHT_COLOR not in title_colors(gui, won=False)
    assert HIGHLIGHT_COLOR in title_colors(gui, won=True)
    assert GAME_OVER_COLOR not in title_colors(gui, won=True)


@pytest.mark.parametrize("size", [(1280, 720), (1440, 900), (1920, 1080)])
def test_end_screen_fits_usual_screens(gui: GUI,
                                       size: tuple[int, int]) -> None:
    """Logo, title, name box and buttons stay inside, one under another."""
    gui.resize(pygame.display.set_mode(size))
    screen = gui.screen.get_rect()
    box, (save, leave) = gui.name_box_rect(), gui.end_rects()
    title_y = gui._end_rows()[0]
    assert title_y >= gui._logo_top() + gui.logo.get_height()
    assert box.top > title_y and save.top > box.bottom
    assert save.bottom <= leave.top
    for rect in (box, save, leave):
        assert screen.contains(rect)
    small_h = gui.small_font.get_height()
    assert leave.bottom <= gui.height - MARGIN - small_h * 2  # above hint
    for won in (True, False):
        for error in (True, False):
            gui.draw_game_end(won, 92482298420, "x" * 20, 1, error)


def test_end_buttons_are_clickable(gui: GUI) -> None:
    """Each end-screen button answers to a click on its centre only."""
    for index, rect in enumerate(gui.end_rects()):
        assert gui.end_item_at(rect.center) == index
    assert gui.end_item_at(gui.name_box_rect().center) is None


def default_sizes() -> list[tuple[int, int]]:
    """Return the (width, height) of each default level, in cells."""
    return [(level.width, level.height) for level in Config().levels]


@pytest.mark.parametrize("size", [(1280, 720), (1400, 800), (1440, 900),
                                  (1920, 1080)])
def test_every_level_shares_the_biggest_maze_left_edge(
        gui: GUI, size: tuple[int, int]) -> None:
    """All levels start on the left edge of the biggest maze, centred
    on its height; the biggest maze stays where it always was."""
    gui.resize(pygame.display.set_mode(size))
    levels = default_sizes()
    frame = gui.maze_frame(levels)
    for width, height in levels:
        gui.set_layout(width, height)  # centred, as without a frame
        if width * gui.tile == frame.width:
            assert gui.offset == frame.topleft
    for width, height in levels:
        gui.set_layout(width, height, frame)
        x, y = gui.offset
        assert x == frame.left
        assert y == frame.top + (frame.height - height * gui.tile) // 2
        assert x >= gui.panel_width and y >= MARGIN
        assert x + width * gui.tile <= size[0] - MARGIN
        assert y + height * gui.tile <= size[1] - MARGIN


def test_frame_example_on_a_1400_x_800_window(gui: GUI) -> None:
    """The 750 px mazes (15x15, 25x25) make the frame, not the 42x42.

    HUD panel 330 px (as wide as BACK needs), free area 1045 x 750 px:
    the frame is 750 px at (477, 25). The 5x5 maze (250 px) starts on
    its left edge, centred on its height: (477, 275).
    """
    assert gui.panel_width == 330
    frame = gui.maze_frame(default_sizes())
    assert frame == pygame.Rect(477, 25, 750, 750)
    gui.set_layout(5, 5, frame)
    assert gui.offset == (477, 275)


def test_frame_of_non_square_levels(gui: GUI) -> None:
    """Its width is the widest maze, its height the tallest: both fit."""
    levels = [(50, 10), (10, 50)]
    frame = gui.maze_frame(levels)
    for width, height in levels:
        gui.set_layout(width, height, frame)
        assert gui.offset[0] == frame.left
        assert frame.contains(pygame.Rect(gui.offset, (width * gui.tile,
                                                       height * gui.tile)))
    gui.set_layout(50, 10)
    assert (frame.left, frame.width) == (gui.offset[0], 50 * gui.tile)
    gui.set_layout(10, 50)
    assert (frame.top, frame.height) == (gui.offset[1], 50 * gui.tile)


def test_cheat_buttons_are_clickable(gui: GUI) -> None:
    """Each cheat button answers to a click on its centre only."""
    rects = gui.panel_rects("cheat")
    assert len(rects) == 4
    for index, rect in enumerate(rects):
        assert gui.panel_item_at("cheat", rect.center) == index
    assert gui.panel_item_at("cheat", (0, 0)) is None


@pytest.mark.parametrize("size", [(1280, 720), (1440, 900), (1920, 1080)])
def test_cheat_menu_fits_usual_screens(gui: GUI,
                                       size: tuple[int, int]) -> None:
    """The taller cheat panel still fits, centred, with its buttons."""
    gui.resize(pygame.display.set_mode(size))
    panel = gui.panel_rect("cheat")
    assert panel.center == (size[0] // 2, size[1] // 2)
    assert gui.screen.get_rect().contains(panel)
    assert gui.panel_backgrounds["cheat"].get_size() == panel.size
    for rect in gui.panel_rects("cheat"):
        assert panel.contains(rect)
    gui.draw_cheat(2, 92482298420, 10, 9, 600.0, (True, False))


def colors_on_line(gui: GUI, rect: pygame.Rect) -> set[tuple[int, ...]]:
    """Return the colors drawn right of rect, on its line, in the panel."""
    panel = gui.panel_rect("cheat")
    return {tuple(gui.screen.get_at((x, y)))[:3]
            for x in range(rect.right, panel.right)
            for y in range(rect.top, rect.bottom)}


def test_toggles_show_on_in_green_and_off_in_red(gui: GUI) -> None:
    """INVINCIBLE ON is green, FREEZE GHOSTS OFF is red; actions none."""
    gui.draw_cheat(0, 0, 1, 3, 90.0, (True, False))
    invincible, freeze, skip, _ = gui.panel_rects("cheat")
    assert CHEAT_ON_COLOR in colors_on_line(gui, invincible)
    assert GAME_OVER_COLOR in colors_on_line(gui, freeze)
    assert not {CHEAT_ON_COLOR, GAME_OVER_COLOR} & colors_on_line(gui, skip)
