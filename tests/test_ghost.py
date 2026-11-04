"""Tests for src/ghost.py: how a ghost chooses its way."""
import random

import pytest

from src.game.level import Level
from src.ghost import (FRIGHT_TIME, RESPAWN_DELAY, Clyde, Ghost, Inky, Pinky,
                       free_cells)
from src.parser import Config, LevelSize
from src.player import Player

# 3 x 3 ring around a closed cell (15); (0, 1) is a dead end that only
# opens upwards: a wall separates it from (0, 2).
RING = [[9, 5, 3], [14, 15, 10], [13, 5, 6]]
# 7 cells in a row, closed at both ends: a straight corridor.
CORRIDOR = [[13, 5, 5, 5, 5, 5, 7]]
# 3 x 3 cells with no inner wall: (1, 1) is a crossing of four ways.
OPEN = [[9, 1, 3], [8, 0, 2], [12, 4, 6]]


def test_default_speed_is_90_percent_of_pacman() -> None:
    """Ghosts are a bit slower than Pac-Man."""
    assert Ghost("blinky", (0, 0)).speed == pytest.approx(3.6)


def test_follows_the_corridors_not_the_straight_line() -> None:
    """(0, 1) is next to the target as the crow flies, but a dead end."""
    ghost = Ghost("blinky", (0, 0))
    ghost.target = (0, 2)
    assert ghost.choose_direction(RING) == "right"


def test_never_turns_back_on_its_own() -> None:
    """Even with its target behind, a ghost keeps going."""
    ghost = Ghost("blinky", (1, 0))
    ghost.direction, ghost.target = "right", (0, 0)
    assert ghost.choose_direction(RING) == "right"


def test_turns_back_in_a_dead_end() -> None:
    """In a dead end, going back is the only way out."""
    ghost = Ghost("blinky", (0, 1))
    ghost.direction = "down"
    assert ghost.choose_direction(RING) == "up"


def test_blinky_aims_at_pacman() -> None:
    """Blinky's target is the cell of Pac-Man."""
    ghost, player = Ghost("blinky", (2, 0)), Player((0, 2))
    ghost.chase(player, RING)
    assert ghost.target == (0, 2)


def test_pinky_aims_four_cells_ahead_of_pacman() -> None:
    """Pinky aims where Pac-Man gets to by going straight on."""
    pinky, player = Pinky("pinky", (6, 0)), Player((0, 0))
    player.facing = "right"
    pinky.chase(player, CORRIDOR)
    assert pinky.target == (4, 0)


def test_pinky_target_stays_in_the_grid() -> None:
    """Only 2 cells are left ahead of Pac-Man: the target stops there."""
    pinky, player = Pinky("pinky", (0, 0)), Player((4, 0))
    player.facing = "right"
    pinky.chase(player, CORRIDOR)
    assert pinky.target == (6, 0)


def test_pinky_aims_through_walls() -> None:
    """A wall right ahead of Pac-Man does not stop the target."""
    pinky, player = Pinky("pinky", (2, 0)), Player((0, 1))
    player.facing = "down"  # (0, 1) is closed below
    pinky.chase(player, RING)
    assert pinky.target == (0, 2)


def test_pinky_never_aims_into_the_42() -> None:
    """A target in a closed "42" cell falls back on Pac-Man's cell."""
    maze = [[13, 5, 5, 7, 15]]  # the last cell is closed
    pinky, player = Pinky("pinky", (3, 0)), Player((0, 0))
    player.facing = "right"
    pinky.chase(player, maze)
    assert pinky.target == (0, 0)


def test_catches_a_still_pacman_on_a_real_maze() -> None:
    """From its corner, Blinky reaches Pac-Man in the middle of a maze."""
    level = Level(LevelSize(width=15, height=15), Config(), 42)
    ghost, player = level.ghosts[0], level.player
    for _ in range(60 * 20):  # at most 20 seconds
        ghost.chase(player, level.maze)
        ghost.update(level.maze, 1 / 60)
        if ghost.touches(player):
            break
    assert ghost.touches(player)


def inky_choices(inky: Inky, maze: list[list[int]],
                 direction: str | None) -> set[str | None]:
    """Return every way Inky takes in 300 tries from the same spot."""
    seen: set[str | None] = set()
    for _ in range(300):
        inky.direction = direction
        seen.add(inky.choose_direction(maze))
    return seen


def test_inky_wanders_but_never_turns_back() -> None:
    """Random ways are open ones, never back where it comes from."""
    inky = Inky("inky", (1, 1))
    inky.rng = random.Random(42)
    inky.target = (2, 1)
    assert inky_choices(inky, OPEN, "right") == {"up", "down", "right"}


def test_inky_without_randomness_chases_like_blinky(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """With no randomness, Inky always takes the shortest way."""
    monkeypatch.setattr("src.ghost.INKY_RANDOMNESS", 0.0)
    inky = Inky("inky", (1, 1))
    inky.target = (2, 1)
    assert inky_choices(inky, OPEN, "right") == {"right"}


def test_edible_inky_flees_instead_of_wandering(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Even when always random, an edible Inky runs away from Pac-Man."""
    monkeypatch.setattr("src.ghost.INKY_RANDOMNESS", 1.0)
    inky = Inky("inky", (0, 0))
    inky.frighten()
    inky.flee(Player((2, 0)))
    assert inky_choices(inky, RING, None) == {"down"}


def test_inky_randomness_survives_the_maze_seed() -> None:
    """The maze package reseeds random for level 1, not Inky's generator."""
    draws = []
    for _ in range(2):
        inky = Level(LevelSize(width=15, height=15), Config(), 42).ghosts[2]
        assert isinstance(inky, Inky)
        draws.append(inky.rng.random())
    assert draws[0] != draws[1]


def test_an_edible_ghost_runs_away() -> None:
    """Edible, it takes the way farthest from Pac-Man, not the closest."""
    ghost, player = Ghost("blinky", (0, 0)), Player((2, 0))
    ghost.chase(player, RING)
    assert ghost.choose_direction(RING) == "right"
    ghost.frighten()
    ghost.flee(player)
    assert ghost.choose_direction(RING) == "down"


def test_an_edible_ghost_turns_dangerous_again() -> None:
    """After FRIGHT_TIME seconds, the ghost can no longer be eaten."""
    ghost = Ghost("blinky", (0, 0))
    ghost.frighten()
    ghost.update(RING, FRIGHT_TIME / 2)
    assert ghost.edible
    ghost.update(RING, FRIGHT_TIME / 2)
    assert not ghost.edible


def test_an_edible_ghost_moves_at_half_speed() -> None:
    """While Pac-Man's speed crosses a cell, an edible ghost crosses half."""
    ghost = Ghost("blinky", (0, 0))
    ghost.frighten()
    ghost.update(CORRIDOR, 1 / ghost.speed)
    assert ghost.progress == pytest.approx(0.5)


def test_eaten_eyes_go_home_and_wait() -> None:
    """The eyes go back to the corner and wait there until RESPAWN_DELAY."""
    ghost = Ghost("blinky", (6, 0))
    ghost.cell = (1, 0)
    ghost.frighten()
    ghost.get_eaten()
    assert ghost.eaten and not ghost.edible
    ghost.update(CORRIDOR, 1.0)  # 5 cells: only at twice 3.6 cells/s
    assert ghost.home and ghost.eaten  # home, but still waiting
    ghost.update(CORRIDOR, RESPAWN_DELAY - 1.0)
    assert ghost.home and not ghost.eaten


def test_eyes_revive_only_once_home() -> None:
    """Even when RESPAWN_DELAY is over, the eyes first reach the corner."""
    ghost = Ghost("blinky", (6, 0))
    ghost.cell = (1, 0)
    ghost.get_eaten()
    ghost.respawn_time = 0.1  # almost over, but far from home
    ghost.update(CORRIDOR, 0.2)
    assert ghost.eaten and not ghost.home


def test_touches_means_less_than_half_a_cell() -> None:
    """Two movers touch when they are less than half a cell apart."""
    ghost, other = Ghost("blinky", (0, 0)), Ghost("blinky", (1, 0))
    assert not ghost.touches(other)
    other.direction, other.progress = "left", 0.6  # now at x = 0.4
    assert ghost.touches(other)


def test_free_cells_skip_the_42() -> None:
    """Every cell but the closed ones, row by row."""
    assert free_cells(RING) == [(0, 0), (1, 0), (2, 0), (0, 1), (2, 1),
                                (0, 2), (1, 2), (2, 2)]


def test_clyde_draws_a_new_target_at_a_crossing() -> None:
    """At a crossing, the target is a random cell, never in the "42"."""
    clyde = Clyde("clyde", (1, 1))
    clyde.rng = random.Random(42)
    targets = set()
    for _ in range(300):
        clyde.direction = None  # (1, 1) of OPEN: four ways out
        clyde.choose_direction(OPEN)
        targets.add(clyde.target)
    assert targets == set(free_cells(OPEN))  # every cell, in the end


def test_clyde_never_aims_into_the_42() -> None:
    """The closed centre of RING is never drawn."""
    clyde = Clyde("clyde", (0, 0))
    clyde.rng = random.Random(42)
    for _ in range(300):
        clyde.direction = None  # (0, 0) of RING: right and down
        clyde.choose_direction(RING)
        assert clyde.target != (1, 1)


def test_clyde_keeps_its_target_in_a_corridor() -> None:
    """With one way forward, no new target is drawn."""
    clyde = Clyde("clyde", (2, 0))
    clyde.direction, clyde.target = "right", (0, 0)
    assert clyde.choose_direction(CORRIDOR) == "right"
    assert clyde.target == (0, 0)


def test_clyde_ignores_pacman() -> None:
    """chase() leaves the target drawn at the last crossing."""
    clyde = Clyde("clyde", (0, 0))
    clyde.target = (2, 2)
    clyde.chase(Player((0, 2)), RING)
    assert clyde.target == (2, 2)


def test_clyde_goes_the_shortest_way_to_its_target(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Once drawn, the target is reached along the corridors (BFS)."""
    clyde = Clyde("clyde", (0, 0))
    monkeypatch.setattr(clyde.rng, "choice", lambda cells: (0, 2))
    assert clyde.choose_direction(RING) == "right"  # (0, 1) is a dead end


def test_edible_clyde_flees_and_eaten_clyde_goes_home() -> None:
    """Never a random target while edible or eaten."""
    clyde = Clyde("clyde", (0, 0))
    clyde.frighten()
    clyde.flee(Player((2, 0)))
    assert clyde.choose_direction(RING) == "down" and clyde.target == (2, 0)
    clyde.get_eaten()
    clyde.cell = (1, 1)
    clyde.choose_direction(OPEN)
    assert clyde.target == (0, 0)


def test_clyde_randomness_survives_the_maze_seed() -> None:
    """The maze package reseeds random for level 1, not Clyde's own."""
    draws = []
    for _ in range(2):
        clyde = Level(LevelSize(width=15, height=15), Config(), 42).ghosts[3]
        assert isinstance(clyde, Clyde)
        draws.append(clyde.rng.random())
    assert draws[0] != draws[1]


def test_clyde_wanders_a_real_maze() -> None:
    """Over a minute, Clyde follows the corridors and visits many cells."""
    level = Level(LevelSize(width=15, height=15), Config(), 42)
    clyde = level.ghosts[3]
    assert isinstance(clyde, Clyde)
    clyde.rng = random.Random(42)
    visited = {clyde.cell}
    for _ in range(60 * 60):
        clyde.update(level.maze, 1 / 60)
        visited.add(clyde.cell)
    assert len(visited) > 50
    assert not set(level.logo) & visited
