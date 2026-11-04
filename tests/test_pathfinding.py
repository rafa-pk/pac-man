"""Tests for src/pathfinding.py: distances along the corridors."""
from src.pathfinding import distances_from

CORRIDOR = [[13, 5, 7]]
# 3 x 3 ring around a closed cell (15); (0, 1) only opens upwards.
RING = [[9, 5, 3], [14, 15, 10], [13, 5, 6]]


def test_distances_along_a_corridor() -> None:
    """Each cell is one step further than the previous one."""
    assert distances_from(CORRIDOR, (2, 0)) == {(2, 0): 0, (1, 0): 1,
                                                (0, 0): 2}


def test_distances_go_around_the_walls() -> None:
    """(0, 1) is next to (0, 2), but a wall forces the long way round."""
    distances = distances_from(RING, (0, 2))
    assert distances[(1, 0)] == 5
    assert distances[(0, 1)] == 7


def test_closed_cells_are_never_reached() -> None:
    """A "42" cell (four walls) gets no distance."""
    assert (1, 1) not in distances_from(RING, (0, 0))
