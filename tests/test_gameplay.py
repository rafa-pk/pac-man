"""Tests for src/game/gameplay.py: eating, score and level changes."""
import math
from pathlib import Path

import pygame
import pytest

from src.game.gameplay import Gameplay
from src.game.scores import Scores
from src.gui import GUI
from src.parser import Config
from src.mover import DIRECTIONS, can_move

ROOT = Path(__file__).resolve().parent.parent


class FakeApp:
    """Stands for the Pacman state machine."""

    running = True
    game_active = True
    state = "game"
    finished = False
    win = False
    final_score = 0


@pytest.fixture
def app() -> FakeApp:
    """The fake state machine the game session talks to."""
    return FakeApp()


@pytest.fixture
def gameplay(app: FakeApp, monkeypatch: pytest.MonkeyPatch,
             tmp_path: Path) -> Gameplay:
    """A game session on the default configuration, without a window."""
    monkeypatch.chdir(ROOT)  # the assets are loaded with relative paths
    pygame.init()
    screen = pygame.display.set_mode((1400, 800))
    scores = Scores(str(tmp_path / "scores.json"))
    return Gameplay(app, Config(), scores, GUI(screen, app))


def clear(gameplay: Gameplay) -> None:
    """Eat everything in the current level at once."""
    gameplay.level.available_pacgums.clear()
    gameplay.level.available_super_pacgums.clear()


def test_eating_a_pacgum_adds_its_points(gameplay: Gameplay) -> None:
    """Reaching a cell with a pacgum eats it and adds 10 points."""
    level = gameplay.level
    start = level.player_start
    direction = next(d for d in DIRECTIONS if can_move(level.maze, start, d))
    dx, dy, _ = DIRECTIONS[direction]
    target = (start[0] + dx, start[1] + dy)
    level.available_pacgums.add(target)
    level.player.turn(direction)
    gameplay.update([], 1 / level.player.speed)  # exactly one cell
    assert target not in level.available_pacgums
    assert gameplay.score == 10
    gameplay.draw()  # the HUD shows the score without error


def test_clearing_a_level_loads_the_next_one(gameplay: Gameplay) -> None:
    """With nothing left to eat, the next level starts; the score stays."""
    gameplay.score = 1234
    clear(gameplay)
    gameplay.update([], 0)
    assert gameplay.level_index == 1
    assert gameplay.level.dimensions == (10, 10)
    assert gameplay.score == 1234


def test_last_level_is_a_victory(gameplay: Gameplay, app: FakeApp) -> None:
    """After the last level, the game ends as won, with its score."""
    gameplay._load_level(len(gameplay.config.levels) - 1)
    gameplay.score = 4321
    clear(gameplay)
    gameplay.update([], 0)
    assert (app.finished, app.win, app.final_score) == (True, True, 4321)
    assert app.game_active is False


def test_ghosts_start_in_their_corners(gameplay: Gameplay) -> None:
    """One ghost per corner, each a bit slower than Pac-Man."""
    width, height = gameplay.level.dimensions
    blinky, pinky, inky, clyde = gameplay.level.ghosts
    assert (blinky.name, blinky.cell) == ("blinky", (width - 1, 0))
    assert (pinky.name, pinky.cell) == ("pinky", (0, 0))
    assert (inky.name, inky.cell) == ("inky", (width - 1, height - 1))
    assert (clyde.name, clyde.cell) == ("clyde", (0, height - 1))
    for ghost in (blinky, pinky, inky, clyde):
        assert ghost.speed == pytest.approx(0.9 * gameplay.level.player.speed)


def test_a_ghost_catching_pacman_costs_a_life(gameplay: Gameplay) -> None:
    """Caught: one life less, Pac-Man and the ghost back to their start."""
    player, ghost = gameplay.level.player, gameplay.level.ghosts[0]
    player.cell = ghost.cell = (1, 1)
    gameplay.update([], 0)
    assert gameplay.lives == 2
    assert player.cell == player.start_position
    assert ghost.cell == ghost.start_position


def test_a_super_pacgum_makes_the_ghosts_edible(gameplay: Gameplay) -> None:
    """Reaching a super-pacgum adds 50 points and frightens every ghost."""
    level = gameplay.level
    start = level.player_start
    direction = next(d for d in DIRECTIONS if can_move(level.maze, start, d))
    dx, dy, _ = DIRECTIONS[direction]
    target = (start[0] + dx, start[1] + dy)
    level.available_pacgums.discard(target)
    level.available_super_pacgums.add(target)
    level.player.turn(direction)
    gameplay.update([], 1 / level.player.speed)  # exactly one cell
    assert target not in level.available_super_pacgums
    assert gameplay.score == 50
    assert all(ghost.edible for ghost in level.ghosts)


def test_touching_an_edible_ghost_eats_it(gameplay: Gameplay) -> None:
    """An edible ghost gives its points and leaves; no life is lost."""
    player, ghost = gameplay.level.player, gameplay.level.ghosts[0]
    player.cell = ghost.cell = (1, 1)
    ghost.frighten()
    gameplay.update([], 0)
    assert ghost.eaten
    assert gameplay.score == 200
    assert gameplay.lives == 3


def test_an_eaten_ghost_is_harmless(gameplay: Gameplay) -> None:
    """While it waits to come back, a ghost costs no life."""
    player, ghost = gameplay.level.player, gameplay.level.ghosts[0]
    player.cell = ghost.cell = (1, 1)
    ghost.get_eaten()
    gameplay.update([], 0)
    assert gameplay.lives == 3


def test_eaten_ghosts_are_eyes(gameplay: Gameplay,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    """An eaten ghost is drawn as eyes; an edible one is drawn too."""
    blinky, pinky, _, _ = gameplay.level.ghosts
    blinky.fright_time = 1.9  # edible, flashing
    pinky.get_eaten()
    drawn: list[tuple[str, bool]] = []
    real_draw = gameplay.gui.draw_ghost

    def spy(pos: tuple[float, float], name: str, facing: str,
            fright_time: float = 0.0, eaten: bool = False) -> None:
        """Remember which ghost is drawn, then really draw it."""
        drawn.append((name, eaten))
        real_draw(pos, name, facing, fright_time, eaten)
    monkeypatch.setattr(gameplay.gui, "draw_ghost", spy)
    gameplay.draw()
    assert drawn == [("blinky", False), ("pinky", True), ("inky", False),
                     ("clyde", False)]


def test_time_runs_down(gameplay: Gameplay) -> None:
    """Each frame takes its duration off the time left."""
    gameplay.update([], 1.0)
    assert gameplay.time_left == pytest.approx(89.0)


def test_time_up_costs_a_life(gameplay: Gameplay) -> None:
    """Out of time: one life less, and the timer starts again."""
    gameplay.time_left = 0.5
    gameplay.update([], 1.0)
    assert gameplay.lives == 2
    assert gameplay.time_left == 90.0


def test_the_42_empties_from_the_top(gameplay: Gameplay) -> None:
    """All of the "42" is lit at first, its bottom half at half time."""
    logo = gameplay.level.logo
    assert len(logo) == 18 and gameplay._lit_logo() == logo
    gameplay.time_left = 45.0
    lit = gameplay._lit_logo()
    assert len(lit) == math.ceil(len(logo) / 2)
    assert lit == logo[len(logo) - len(lit):]  # the bottom cells stay
    gameplay.time_left = 0.0
    assert gameplay._lit_logo() == []


def test_losing_the_last_life_is_game_over(gameplay: Gameplay,
                                           app: FakeApp) -> None:
    """With no life left, the game ends as lost, with its score."""
    gameplay.lives, gameplay.score = 1, 120
    gameplay.level.ghosts[0].cell = gameplay.level.player.cell
    gameplay.update([], 0)
    assert (app.finished, app.win, app.final_score) == (True, False, 120)
    assert app.game_active is False


def test_last_life_lost_to_the_timer_is_game_over(gameplay: Gameplay,
                                                  app: FakeApp) -> None:
    """Running out of time on the last life also ends the game."""
    gameplay.lives, gameplay.time_left = 1, 0.5
    gameplay.update([], 1.0)
    assert (app.finished, app.win) == (True, False)


def test_quitting_mid_game_skips_the_end_screen(gameplay: Gameplay,
                                                app: FakeApp) -> None:
    """ESC, BACK or the pause MAIN MENU go straight to the main menu."""
    gameplay.update([key(pygame.K_ESCAPE)], 0)
    assert app.state == "main_menu" and not app.finished


def test_escape_returns_to_the_menu(gameplay: Gameplay, app: FakeApp) -> None:
    """ESC ends the game session and shows the main menu."""
    escape = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE,
                                scancode=pygame.KSCAN_ESCAPE)
    gameplay.update([escape], 0)
    assert (app.state, app.game_active) == ("main_menu", False)


def test_closing_the_window_stops_at_once(gameplay: Gameplay,
                                          app: FakeApp) -> None:
    """The red button stops the program; nothing moves on that frame."""
    player = gameplay.level.player
    player.turn(next(d for d in DIRECTIONS
                     if can_move(gameplay.level.maze, player.cell, d)))
    gameplay.update([pygame.event.Event(pygame.QUIT)], 1.0)
    assert app.running is False
    assert player.position == player.start_position
    assert gameplay.time_left == 90.0


def test_relayout_keeps_the_game(gameplay: Gameplay) -> None:
    """A new window size refits the maze; the game itself goes on."""
    gameplay.score, gameplay.time_left = 1234, 42.0
    gameplay.level.player.cell = (1, 1)
    gameplay.gui.resize(pygame.display.set_mode((1920, 1080)))
    gameplay.relayout()
    width, height = gameplay.level.dimensions
    tile = gameplay.gui.tile
    assert gameplay.surface.get_size() == (width * tile, height * tile)
    assert (gameplay.level_index, gameplay.score, gameplay.time_left,
            gameplay.level.player.cell) == (0, 1234, 42.0, (1, 1))


def test_back_button_returns_to_the_menu(gameplay: Gameplay,
                                         app: FakeApp) -> None:
    """A click on the BACK button also goes back to the main menu."""
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                               pos=gameplay.gui.back_rect().center)
    gameplay.update([click], 0)
    assert (app.state, app.game_active) == ("main_menu", False)


def key(code: int, scancode: int = 0) -> pygame.event.Event:
    """Return the event of a key being pressed."""
    return pygame.event.Event(pygame.KEYDOWN, key=code, scancode=scancode)


def snapshot(gameplay: Gameplay) -> tuple[object, ...]:
    """Return everything that changes while the game runs."""
    movers = [gameplay.level.player, *gameplay.level.ghosts]
    return (gameplay.score, gameplay.lives, gameplay.time_left,
            [(m.cell, m.progress, m.direction) for m in movers],
            [(g.fright_time, g.respawn_time) for g in gameplay.level.ghosts])


def move_pacman(gameplay: Gameplay) -> None:
    """Send Pac-Man down an open corridor, halfway to the next cell."""
    player = gameplay.level.player
    player.turn(next(d for d in DIRECTIONS
                     if can_move(gameplay.level.maze, player.cell, d)))
    gameplay.update([], 0.5 / player.speed)


def test_space_pauses_and_freezes_the_game(gameplay: Gameplay) -> None:
    """SPACE opens the pause menu; then nothing moves, time stands still."""
    move_pacman(gameplay)
    gameplay.level.ghosts[0].frighten()
    gameplay.update([key(pygame.K_SPACE, pygame.KSCAN_SPACE)], 1.0)
    assert gameplay.paused and gameplay.menu_index == 0
    frozen = snapshot(gameplay)
    for _ in range(3):
        gameplay.update([], 1.0)
    assert snapshot(gameplay) == frozen


@pytest.mark.parametrize("code, scancode", [
    (pygame.K_SPACE, pygame.KSCAN_SPACE), (pygame.K_ESCAPE, 0),
    (pygame.K_w, pygame.KSCAN_W), (pygame.K_s, pygame.KSCAN_S),
    (pygame.K_LEFT, 0), (pygame.K_RIGHT, 0)])
def test_other_keys_do_nothing_while_paused(gameplay: Gameplay, app: FakeApp,
                                            code: int, scancode: int) -> None:
    """Only UP/DOWN and ENTER work: SPACE and ESC do not leave the pause."""
    gameplay.update([key(pygame.K_SPACE, pygame.KSCAN_SPACE)], 0)
    frozen = snapshot(gameplay)
    gameplay.update([key(code, scancode)], 1.0)
    assert gameplay.paused and gameplay.menu_index == 0
    assert (app.state, app.game_active) == ("game", True)
    assert snapshot(gameplay) == frozen


def test_up_and_down_choose_a_button(gameplay: Gameplay) -> None:
    """The arrows move between RESUME and MAIN MENU, and wrap around."""
    gameplay.update([key(pygame.K_SPACE, pygame.KSCAN_SPACE)], 0)
    gameplay.update([key(pygame.K_DOWN)], 0)
    assert gameplay.menu_index == 1
    gameplay.update([key(pygame.K_DOWN)], 0)
    assert gameplay.menu_index == 0
    gameplay.update([key(pygame.K_UP)], 0)
    assert gameplay.menu_index == 1


def test_enter_on_resume_goes_on(gameplay: Gameplay) -> None:
    """ENTER on RESUME closes the menu, and the game moves again."""
    gameplay.update([key(pygame.K_SPACE, pygame.KSCAN_SPACE)], 0)
    gameplay.update([key(pygame.K_RETURN)], 0)
    assert not gameplay.paused
    gameplay.update([], 1.0)
    assert gameplay.time_left == pytest.approx(89.0)


def test_enter_on_main_menu_leaves(gameplay: Gameplay, app: FakeApp) -> None:
    """ENTER on MAIN MENU ends the game session."""
    gameplay.update([key(pygame.K_SPACE, pygame.KSCAN_SPACE)], 0)
    gameplay.update([key(pygame.K_DOWN), key(pygame.K_RETURN)], 0)
    assert (app.state, app.game_active) == ("main_menu", False)


@pytest.mark.parametrize("index, paused, state", [
    (0, False, "game"), (1, True, "main_menu")])
def test_mouse_chooses_and_clicks(gameplay: Gameplay, app: FakeApp,
                                  index: int, paused: bool,
                                  state: str) -> None:
    """Hovering a button lights it; a click on it selects it."""
    gameplay.update([key(pygame.K_SPACE, pygame.KSCAN_SPACE)], 0)
    centre = gameplay.gui.panel_rects("pause")[index].center
    gameplay.update([pygame.event.Event(pygame.MOUSEMOTION, pos=centre)], 0)
    assert gameplay.menu_index == index
    gameplay.update([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                        pos=centre)], 0)
    assert (gameplay.paused, app.state) == (paused, state)


def test_click_outside_the_buttons_stays_paused(gameplay: Gameplay,
                                                app: FakeApp) -> None:
    """A click elsewhere, even on the BACK button below, does nothing."""
    gameplay.update([key(pygame.K_SPACE, pygame.KSCAN_SPACE)], 0)
    for pos in ((0, 0), gameplay.gui.back_rect().center):
        gameplay.update([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                            pos=pos)], 0)
    assert gameplay.paused and app.state == "game"


def test_closing_the_window_while_paused(gameplay: Gameplay,
                                         app: FakeApp) -> None:
    """The red button still stops the program during the pause."""
    gameplay.update([key(pygame.K_SPACE, pygame.KSCAN_SPACE)], 0)
    gameplay.update([pygame.event.Event(pygame.QUIT)], 0)
    assert app.running is False


def test_pause_menu_is_drawn_with_both_scores(
        gameplay: Gameplay, monkeypatch: pytest.MonkeyPatch) -> None:
    """While paused, the menu is drawn over the game with both scores."""
    gameplay.scores.add_entry("best", 5000)
    gameplay.score = 1234
    drawn: list[tuple[int, int, int]] = []
    real_draw = gameplay.gui.draw_pause

    def spy(selected: int, score: int, high_score: int) -> None:
        """Remember what the pause menu shows, then really draw it."""
        drawn.append((selected, score, high_score))
        real_draw(selected, score, high_score)
    monkeypatch.setattr(gameplay.gui, "draw_pause", spy)
    gameplay.draw()
    assert drawn == []  # not paused: no menu
    gameplay.update([key(pygame.K_SPACE, pygame.KSCAN_SPACE)], 0)
    gameplay.draw()
    assert drawn == [(0, 1234, 5000)]


def test_high_score_is_the_saved_best(gameplay: Gameplay) -> None:
    """0 with no saved score; the saved best, even below the current one."""
    assert gameplay._high_score() == 0
    gameplay.scores.add_entry("best", 300)
    gameplay.score = 9999
    assert gameplay._high_score() == 300


def test_maze_left_edge_stays_put_across_levels(gameplay: Gameplay) -> None:
    """Every level starts on the same left edge, centred on the height of
    the biggest maze, even after the window is resized."""
    for size in ((1400, 800), (1920, 1080)):
        gameplay.gui.resize(pygame.display.set_mode(size))
        lefts = set()
        for index in range(len(gameplay.config.levels)):
            gameplay._load_level(index)
            frame = gameplay.gui.maze_frame(
                [(lv.width, lv.height) for lv in gameplay.config.levels])
            x, y = gameplay.gui.offset
            height = gameplay.level.dimensions[1] * gameplay.gui.tile
            assert y == frame.top + (frame.height - height) // 2
            lefts.add(x)
        assert lefts == {frame.left}


CHEAT = key(pygame.K_c)
INVINCIBLE, FREEZE, SKIP, RESUME = range(4)  # the cheat menu buttons


def cheat(gameplay: Gameplay, *indexes: int) -> None:
    """Open the cheat menu and select the buttons at indexes, in order."""
    gameplay.update([CHEAT], 0)
    for index in indexes:
        centre = gameplay.gui.panel_rects("cheat")[index].center
        gameplay.update([pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                            button=1, pos=centre)], 0)


def touch_a_dangerous_ghost(gameplay: Gameplay) -> None:
    """Put Blinky on Pac-Man's cell, then play one still frame."""
    gameplay.level.ghosts[0].cell = gameplay.level.player.cell
    gameplay.update([], 0)


def test_c_opens_the_cheat_menu_and_freezes(gameplay: Gameplay) -> None:
    """C opens the cheat menu on its first button; nothing moves."""
    move_pacman(gameplay)
    gameplay.update([CHEAT], 1.0)
    assert (gameplay.menu, gameplay.menu_index) == ("cheat", 0)
    frozen = snapshot(gameplay)
    gameplay.update([], 1.0)
    assert snapshot(gameplay) == frozen


@pytest.mark.parametrize("code, scancode", [
    (pygame.K_c, 0), (pygame.K_SPACE, pygame.KSCAN_SPACE),
    (pygame.K_ESCAPE, 0)])
def test_keys_do_not_close_the_cheat_menu(gameplay: Gameplay, app: FakeApp,
                                          code: int, scancode: int) -> None:
    """Only RESUME closes it: C, SPACE and ESC do nothing."""
    gameplay.update([CHEAT], 0)
    gameplay.update([key(code, scancode)], 1.0)
    assert gameplay.menu == "cheat" and app.state == "game"


def test_arrows_go_through_the_four_cheat_buttons(gameplay: Gameplay) -> None:
    """DOWN goes from INVINCIBLE to RESUME, then wraps back."""
    gameplay.update([CHEAT], 0)
    for index in (1, 2, 3, 0):
        gameplay.update([key(pygame.K_DOWN)], 0)
        assert gameplay.menu_index == index


def test_toggles_switch_on_and_off(gameplay: Gameplay) -> None:
    """ENTER or a click switches a toggle; the menu stays open."""
    gameplay.update([CHEAT], 0)  # opening a menu ends the frame
    gameplay.update([key(pygame.K_RETURN)], 0)
    assert gameplay.invincible and gameplay.menu == "cheat"
    gameplay.update([key(pygame.K_DOWN), key(pygame.K_RETURN)], 0)
    assert gameplay.ghosts_frozen
    gameplay.update([key(pygame.K_RETURN)], 0)
    assert not gameplay.ghosts_frozen
    cheat(gameplay, INVINCIBLE)
    assert not gameplay.invincible


def test_resume_closes_the_cheat_menu(gameplay: Gameplay) -> None:
    """RESUME goes back to the game, which moves again."""
    cheat(gameplay, RESUME)
    assert gameplay.menu is None
    gameplay.update([], 1.0)
    assert gameplay.time_left == pytest.approx(89.0)


def test_invincible_pacman_goes_through_ghosts(gameplay: Gameplay) -> None:
    """With INVINCIBLE on, a dangerous ghost costs no life."""
    cheat(gameplay, INVINCIBLE, RESUME)
    touch_a_dangerous_ghost(gameplay)
    assert gameplay.lives == 3
    assert gameplay.level.ghosts[0].cell == gameplay.level.player.cell


def test_invincibility_does_not_stop_the_timer(gameplay: Gameplay) -> None:
    """Out of time still costs a life, even when invincible."""
    cheat(gameplay, INVINCIBLE, RESUME)
    gameplay.time_left = 0.5
    gameplay.update([], 1.0)
    assert gameplay.lives == 2


def test_invincible_pacman_still_eats_blue_ghosts(gameplay: Gameplay) -> None:
    """An edible ghost is still eaten for its points."""
    cheat(gameplay, INVINCIBLE, RESUME)
    gameplay.level.ghosts[0].frighten()
    touch_a_dangerous_ghost(gameplay)
    assert gameplay.level.ghosts[0].eaten and gameplay.score == 200


def test_frozen_ghosts_stand_still(gameplay: Gameplay) -> None:
    """With FREEZE GHOSTS on, the ghosts and their timers stop."""
    cheat(gameplay, FREEZE, RESUME)
    gameplay.level.ghosts[1].frighten()
    before = [(g.cell, g.progress, g.fright_time)
              for g in gameplay.level.ghosts]
    gameplay.update([], 2.0)
    assert [(g.cell, g.progress, g.fright_time)
            for g in gameplay.level.ghosts] == before
    assert gameplay.time_left == pytest.approx(88.0)  # the game goes on


def test_a_frozen_ghost_is_still_dangerous(gameplay: Gameplay) -> None:
    """Walking into a frozen ghost costs a life, unless invincible."""
    cheat(gameplay, FREEZE, RESUME)
    touch_a_dangerous_ghost(gameplay)
    assert gameplay.lives == 2


def test_skip_level_loads_the_next_one(gameplay: Gameplay) -> None:
    """SKIP LEVEL starts the next level at once, menu closed."""
    gameplay.score = 50
    cheat(gameplay, SKIP)
    assert (gameplay.level_index, gameplay.menu) == (1, None)
    assert gameplay.level.dimensions == (10, 10)
    assert gameplay.score == 50  # skipped pacgums give nothing


def test_skipping_the_last_level_wins(gameplay: Gameplay,
                                      app: FakeApp) -> None:
    """On the last level, SKIP LEVEL opens the victory screen."""
    gameplay._load_level(len(gameplay.config.levels) - 1)
    cheat(gameplay, SKIP)
    assert (app.finished, app.win) == (True, True)


def test_cheats_last_across_levels(gameplay: Gameplay) -> None:
    """A cheat stays on in the next levels, until switched off."""
    cheat(gameplay, INVINCIBLE, FREEZE, SKIP)
    assert gameplay.level_index == 1
    assert gameplay.invincible and gameplay.ghosts_frozen


def test_cheat_menu_is_drawn_with_the_game_state(
        gameplay: Gameplay, monkeypatch: pytest.MonkeyPatch) -> None:
    """The menu shows score, level, lives, time left and the toggles."""
    gameplay.score, gameplay.lives, gameplay.time_left = 1234, 2, 67.0
    drawn: list[tuple[object, ...]] = []
    real_draw = gameplay.gui.draw_cheat

    def spy(*args: object) -> None:
        """Remember what the cheat menu shows, then really draw it."""
        drawn.append(args)
        real_draw(*args)  # type: ignore[arg-type]
    monkeypatch.setattr(gameplay.gui, "draw_cheat", spy)
    cheat(gameplay, FREEZE)  # a click without hovering: 0 stays lit
    gameplay.draw()
    assert drawn == [(0, 1234, 1, 2, 67.0, (False, True))]
