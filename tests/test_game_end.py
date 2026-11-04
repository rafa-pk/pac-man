"""Tests for the end screen of pac-man.py: name input and saved score."""
import importlib
from pathlib import Path
from typing import Any

import pygame
import pytest

from src.game.scores import Scores

ROOT = Path(__file__).resolve().parent.parent
pacman_module = importlib.import_module("pac-man")


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    """The program on its game-over screen, its main loop switched off.

    The scores are kept in a temporary file, never in data/.
    """
    monkeypatch.chdir(ROOT)  # the assets are loaded with relative paths
    monkeypatch.setattr(pacman_module.Pacman, "_run", lambda self: None)
    program = pacman_module.Pacman(str(ROOT / "config.json"))
    program.scores = Scores(str(tmp_path / "scores.json"))
    program.state, program.finished = "game_end", True
    program.win, program.final_score = False, 1234
    return program


def typed(text: str) -> pygame.event.Event:
    """Return the event of text being typed."""
    return pygame.event.Event(pygame.TEXTINPUT, text=text)


def key(code: int) -> pygame.event.Event:
    """Return the event of a key being pressed."""
    return pygame.event.Event(pygame.KEYDOWN, key=code, scancode=0)


def click(pos: tuple[int, int]) -> pygame.event.Event:
    """Return the event of a left click at pos."""
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def test_game_over_opens_the_end_screen(app: Any) -> None:
    """A game lost on its last life leads to the end screen."""
    app.state, app.finished = "game", False
    app._game([], 0)  # starts a new game
    app.gameplay.lives, app.gameplay.score = 1, 70
    app.gameplay.level.ghosts[0].cell = app.gameplay.level.player.cell
    app._game([], 0)
    assert (app.state, app.win, app.final_score) == ("game_end", False, 70)


def test_typing_fills_the_name_box(app: Any) -> None:
    """Typed text is added, BACKSPACE erases the last character."""
    app._game_end([typed("Ra"), typed("fa"), key(pygame.K_BACKSPACE)], 0)
    assert app.player_name == "Raf"


def test_name_box_keeps_every_character_up_to_its_size(app: Any) -> None:
    """Nothing is filtered while typing; the box stops at its size."""
    app._game_end([typed("é-!"), typed("x" * 30)], 0)
    assert app.player_name == "é-!" + "x" * 17
    assert len(app.player_name) == 20


def test_valid_name_saves_then_shows_the_high_scores(app: Any) -> None:
    """SAVE SCORE adds the entry and opens HIGHSCORES, ready for a game."""
    app._game_end([typed("rafa 42"), key(pygame.K_RETURN)], 0)
    assert app.scores.fetch_entries() == [{"name": "rafa 42", "score": 1234}]
    assert app.state == "highscores"
    assert not app.finished and not app.name_error
    assert app.player_name == ""


@pytest.mark.parametrize("name", ["", "elevenchars", "a-b", "é", "rafa!"])
def test_invalid_name_is_refused_and_cleared(app: Any, name: str) -> None:
    """A name that breaks the rule: nothing saved, box cleared, error."""
    app._game_end([typed(name), key(pygame.K_RETURN)], 0)
    assert app.scores.fetch_entries() == []
    assert (app.state, app.player_name, app.name_error) == ("game_end", "",
                                                            True)


def test_typing_again_hides_the_error(app: Any) -> None:
    """The error stays until the player types a new name."""
    app._game_end([key(pygame.K_RETURN)], 0)
    assert app.name_error
    app._game_end([typed("r")], 0)
    assert not app.name_error


def test_main_menu_leaves_without_saving(app: Any) -> None:
    """DOWN then ENTER on MAIN MENU: home screen, nothing saved."""
    app._game_end([typed("rafa"), key(pygame.K_DOWN), key(pygame.K_RETURN)],
                  0)
    assert app.state == "main_menu" and not app.finished
    assert app.scores.fetch_entries() == []


def test_up_and_down_choose_a_button(app: Any) -> None:
    """The arrows move between SAVE SCORE and MAIN MENU, and wrap."""
    app._game_end([key(pygame.K_UP)], 0)
    assert app.end_index == 1
    app._game_end([key(pygame.K_DOWN)], 0)
    assert app.end_index == 0


@pytest.mark.parametrize("index, state", [(0, "highscores"),
                                          (1, "main_menu")])
def test_mouse_chooses_and_clicks(app: Any, index: int, state: str) -> None:
    """Hovering a button lights it; a click on it selects it."""
    centre = app.gui.end_rects()[index].center
    app._game_end([typed("rafa"),
                   pygame.event.Event(pygame.MOUSEMOTION, pos=centre)], 0)
    assert app.end_index == index
    app._game_end([click(centre)], 0)
    assert app.state == state


def test_click_outside_the_buttons_does_nothing(app: Any) -> None:
    """A click on the name box or elsewhere selects no button."""
    app._game_end([typed("rafa"), click(app.gui.name_box_rect().center),
                   click((0, 0))], 0)
    assert app.state == "game_end" and app.scores.fetch_entries() == []


@pytest.mark.parametrize("event", [
    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, scancode=0),
    pygame.event.Event(pygame.QUIT)])
def test_escape_or_close_quits_the_program(app: Any,
                                           event: pygame.event.Event) -> None:
    """ESC closes the program, like the red button of the window."""
    app._game_end([event], 0)
    assert app.running is False
    assert app.scores.fetch_entries() == []


def test_next_game_starts_normally(app: Any) -> None:
    """After the end screen, a new game does not end at once."""
    app._game_end([typed("rafa"), key(pygame.K_RETURN)], 0)
    app.state = "game"
    app._game([], 0)
    assert app.state == "game" and app.game_active
