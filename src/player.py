"""Pac-Man: moved by the keyboard along the corridors."""
import math

from src.mover import OPPOSITE, Mover, can_move, neighbour

BASE_SPEED = 4.0  # cells per second on the first level
SPEED_PER_LEVEL = 0.2  # added for each following level


def level_speed(index: int) -> float:
    """Return the player speed on the level at position index (0 = first)."""
    return BASE_SPEED + SPEED_PER_LEVEL * index


class Player(Mover):
    """Pac-Man: goes where the keyboard says and never crosses a wall."""

    def __init__(self, start_position: tuple[int, int],
                 speed: float = BASE_SPEED) -> None:
        """Create the player, standing still on its starting cell.

        Args:
            start_position: Starting cell (x, y).
            speed: Speed in cells per second.
        """
        super().__init__(start_position, speed)
        self.wanted: str | None = None  # last direction asked by the player

    @property
    def mouth_opening(self) -> float:
        """Return how open the mouth is, from 0 (closed) to 1 (wide open).

        It closes on each cell centre and opens wide halfway, so Pac-Man
        chomps once per cell; when still, the mouth stays half open.
        """
        if self.direction is None:
            return 0.5
        return abs(math.sin(math.pi * self.progress))

    def respawn(self) -> None:
        """Go back to the starting cell, still, and forget the keys."""
        super().respawn()
        self.wanted = None

    def turn(self, direction: str) -> None:
        """Remember the asked direction; a U-turn happens immediately."""
        self.wanted = direction
        if (self.direction is not None and self.progress > 0
                and direction == OPPOSITE[self.direction]):
            self.cell = neighbour(self.cell, self.direction)
            self.progress = 1 - self.progress
            self.direction = direction
            self.facing = direction

    def choose_direction(self, maze: list[list[int]]) -> str | None:
        """Take the wanted direction if open, else go straight, else stop."""
        for direction in (self.wanted, self.direction):
            if direction is not None and can_move(maze, self.cell, direction):
                return direction
        return None
