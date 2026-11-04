"""Shortest paths along the corridors of the maze."""
from collections import deque

from src.mover import DIRECTIONS, can_move, neighbour


def distances_from(maze: list[list[int]],
                   start: tuple[int, int]) -> dict[tuple[int, int], int]:
    """Return the number of steps from start to every reachable cell.

    Breadth-first search: the cells are numbered in waves (all the cells 1
    step away, then 2 steps, ...), so a cell is first reached through one
    of its shortest paths. Closed cells never get a number.
    """
    distances = {start: 0}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for direction in DIRECTIONS:
            if not can_move(maze, cell, direction):
                continue
            next_cell = neighbour(cell, direction)
            if next_cell not in distances:
                distances[next_cell] = distances[cell] + 1
                queue.append(next_cell)
    return distances
