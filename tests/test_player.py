"""Tests for src/player.py: Pac-Man's movement on the maze grid."""
import random

import pytest

from src.game.level import Level
from src.parser import Config, LevelSize
from src.mover import DIRECTIONS, can_move
from src.player import BASE_SPEED, Player, level_speed

# Three cells in a row, open between them. Walls: 13 = top + bottom + left,
# 5 = top + bottom, 7 = top + bottom + right.
CORRIDOR = [[13, 5, 7]]
# L-shaped path (0, 0) -> (1, 0) -> (1, 1); the cell (0, 1) is closed (15).
ELBOW = [[13, 3], [15, 14]]
STEP = 1 / BASE_SPEED  # time to cross one cell at the default speed
MOVES = {(dx, dy): name for name, (dx, dy, _) in DIRECTIONS.items()}


def test_can_move() -> None:
    """A side is open when its wall bit is not set."""
    assert can_move(CORRIDOR, (0, 0), "right")
    assert not can_move(CORRIDOR, (0, 0), "left")
    assert not can_move(CORRIDOR, (1, 0), "up")


def test_player_waits_for_a_key() -> None:
    """Without any direction, the player stays on its cell."""
    player = Player((0, 0))
    player.update(CORRIDOR, 1.0)
    assert player.position == (0.0, 0.0)


def test_player_glides_between_cells() -> None:
    """Half the time of a step puts the player halfway."""
    player = Player((0, 0))
    player.turn("right")
    player.update(CORRIDOR, STEP / 2)
    assert player.position == pytest.approx((0.5, 0.0))


def test_player_stops_against_a_wall() -> None:
    """The player goes straight to the end of the corridor, then stops."""
    player = Player((0, 0))
    player.turn("right")
    player.update(CORRIDOR, 10.0)
    assert player.position == (2.0, 0.0)
    assert player.direction is None


def test_u_turn_is_immediate() -> None:
    """The opposite direction reverses at once, between two cells."""
    player = Player((0, 0))
    player.turn("right")
    player.update(CORRIDOR, STEP / 2)
    player.turn("left")
    assert player.position == pytest.approx((0.5, 0.0))
    player.update(CORRIDOR, STEP / 2)
    assert player.position == pytest.approx((0.0, 0.0))


def test_turn_is_remembered_until_possible() -> None:
    """A direction asked too early is taken at the next opening."""
    player = Player((0, 0))
    player.turn("right")
    player.update(ELBOW, STEP / 2)
    player.turn("down")  # still a wall below: remembered for later
    player.update(ELBOW, 10.0)
    assert player.position == (1.0, 1.0)


def test_player_never_crosses_a_wall() -> None:
    """Random keys on a real maze: every move goes through an opening."""
    level = Level(LevelSize(width=15, height=15), Config(), 42)
    player = Player(level.player_start)
    chooser = random.Random(0)
    visited = {player.cell}
    for _ in range(3000):
        if chooser.random() < 0.1:
            player.turn(chooser.choice(list(DIRECTIONS)))
        before = player.cell
        player.update(level.maze, 1 / 60)
        if player.cell != before:
            move = (player.cell[0] - before[0], player.cell[1] - before[1])
            assert can_move(level.maze, before, MOVES[move])
            visited.add(player.cell)
    assert len(visited) > 10


def test_speed_grows_with_the_levels() -> None:
    """4 cells/s on level 1, then 0.2 more on each level."""
    assert level_speed(0) == BASE_SPEED == 4.0
    assert level_speed(9) == pytest.approx(5.8)


def test_facing_keeps_the_last_movement() -> None:
    """The mouth points where Pac-Man goes, and stays so once stopped."""
    player = Player((0, 0))
    player.turn("right")
    player.update(CORRIDOR, STEP / 2)
    assert player.facing == "right"
    player.turn("left")  # U-turn
    assert player.facing == "left"
    player.update(CORRIDOR, 10.0)  # back against the left wall
    assert (player.direction, player.facing) == (None, "left")


def test_mouth_chomps_once_per_cell() -> None:
    """Closed on a cell centre, wide open halfway, half open when still."""
    player = Player((0, 0))
    assert player.mouth_opening == 0.5
    player.turn("right")
    player.update(CORRIDOR, STEP / 2)
    assert player.mouth_opening == pytest.approx(1.0)
    player.update(CORRIDOR, STEP / 2)  # reaches the centre of cell 1
    assert player.mouth_opening == pytest.approx(0.0)


def test_update_returns_the_cells_reached() -> None:
    """update() lists every cell reached, so no pacgum is skipped."""
    player = Player((0, 0))
    player.turn("right")
    assert player.update(CORRIDOR, STEP / 2) == []
    assert player.update(CORRIDOR, 10.0) == [(1, 0), (2, 0)]


def test_respawn_puts_pacman_back_still() -> None:
    """After a respawn: on the start cell, still, keys forgotten."""
    player = Player((0, 0))
    player.turn("right")
    player.update(CORRIDOR, STEP * 1.5)
    player.respawn()
    assert player.position == (0.0, 0.0)
    assert (player.direction, player.wanted) == (None, None)
