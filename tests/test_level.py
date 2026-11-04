"""Tests for src/game/level.py: maze generation and player start."""
import pytest

from src.game import level as level_module
from src.game.level import RANDOM_SEED, Level
from src.parser import Config, LevelSize


def make_level(width: int, height: int, seed: int = 42) -> Level:
    """Build a level of the given size with the default configuration."""
    return Level(LevelSize(width=width, height=height), Config(), seed)


def test_every_default_level_generates() -> None:
    """The 10 default levels build without crashing (level 1 is seeded)."""
    config = Config()
    for number, size in enumerate(config.levels):
        seed = config.seed if number == 0 else RANDOM_SEED
        maze = Level(size, config, seed).maze
        assert len(maze) == size.height
        assert all(len(row) == size.width for row in maze)


def test_level_one_is_always_the_same() -> None:
    """A positive seed gives the same maze every time."""
    assert make_level(15, 15).maze == make_level(15, 15).maze


def test_random_levels_differ() -> None:
    """RANDOM_SEED gives a different maze each time."""
    first = make_level(20, 20, RANDOM_SEED).maze
    assert make_level(20, 20, RANDOM_SEED).maze != first


@pytest.mark.parametrize("size", [15, 18, 20, 25, 42])
def test_player_starts_near_the_middle(size: int) -> None:
    """The middle can be inside the "42": the start moves to a free cell."""
    level = make_level(size, size)
    x, y = level.player_start
    assert (x, y) not in level.logo
    assert abs(x - size // 2) + abs(y - size // 2) <= 2


def test_generator_failure_stops_cleanly(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """If the external package crashes, the game stops with a message."""
    def broken(**kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(level_module, "MazeGenerator", broken)
    with pytest.raises(SystemExit):
        make_level(15, 15)
    assert "maze generator failed" in capsys.readouterr().err


def test_no_pacgum_under_the_player() -> None:
    """The starting cell never holds a pacgum."""
    for size in (5, 10, 15, 42):
        level = make_level(size, size)
        assert level.player_start not in level.pacgums


def test_pacgums_are_capped_with_a_message(
        capsys: pytest.CaptureFixture[str]) -> None:
    """A small maze gets one pacgum per free cell, and says so."""
    level = make_level(5, 5)  # 25 cells - 4 corners - 1 start = 20
    assert len(level.pacgums) == 20
    assert "room for 20 pacgums" in capsys.readouterr().err


def test_eat_gives_points_once() -> None:
    """A pacgum gives 10 points once; a super-pacgum gives 50."""
    level = make_level(15, 15)
    pacgum = next(iter(level.pacgums))
    assert level.eat(pacgum) == 10
    assert level.eat(pacgum) == 0
    assert level.eat((0, 0)) == 50  # a corner holds a super-pacgum
    assert level.eat(level.player_start) == 0


def test_level_is_cleared_when_everything_is_eaten() -> None:
    """The level is won once all pacgums and super-pacgums are eaten."""
    level = make_level(15, 15)
    for cell in list(level.pacgums) + level.corners:
        assert not level.cleared
        level.eat(cell)
    assert level.cleared


def test_ghosts_wait_in_their_corners() -> None:
    """Blinky top-right, Pinky top-left, Inky bottom-right, Clyde
    bottom-left."""
    level = make_level(15, 15)
    assert [(g.name, g.cell) for g in level.ghosts] == [
        ("blinky", (14, 0)), ("pinky", (0, 0)), ("inky", (14, 14)),
        ("clyde", (0, 14))]
