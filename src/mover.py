"""Movement on the maze grid, shared by Pac-Man and the ghosts."""
from abc import ABC, abstractmethod

from src.constants import BOTTOM, LEFT, RIGHT, TOP

# direction -> (dx, dy, wall bit that closes this side of a cell)
DIRECTIONS: dict[str, tuple[int, int, int]] = {
    "up": (0, -1, TOP),
    "down": (0, 1, BOTTOM),
    "left": (-1, 0, LEFT),
    "right": (1, 0, RIGHT),
}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


def can_move(maze: list[list[int]], cell: tuple[int, int],
             direction: str) -> bool:
    """Tell whether no wall closes that side of the cell."""
    x, y = cell
    return maze[y][x] & DIRECTIONS[direction][2] == 0


def neighbour(cell: tuple[int, int], direction: str) -> tuple[int, int]:
    """Return the cell next to cell in that direction."""
    dx, dy, _ = DIRECTIONS[direction]
    return cell[0] + dx, cell[1] + dy


class Mover(ABC):
    """Glides from cell to cell along the corridors, never through a wall.

    At each cell centre, the subclass chooses where to go next.
    """

    def __init__(self, start_position: tuple[int, int],
                 speed: float) -> None:
        """Create the mover, standing still on its starting cell.

        Args:
            start_position: Starting cell (x, y).
            speed: Speed in cells per second.
        """
        self.start_position, self.speed = start_position, speed
        self.cell = start_position  # cell being left, or occupied if still
        self.progress = 0.0  # 0 = on self.cell, 1 = on the next cell
        self.direction: str | None = None  # current movement
        self.facing = "right"  # last movement, for drawing

    @property
    def position(self) -> tuple[float, float]:
        """Return the position in cells, between two cells while moving."""
        x, y = self.cell
        if self.direction is None:
            return float(x), float(y)
        dx, dy, _ = DIRECTIONS[self.direction]
        return x + dx * self.progress, y + dy * self.progress

    def respawn(self) -> None:
        """Go back to the starting cell, standing still."""
        self.cell, self.progress = self.start_position, 0.0
        self.direction = None

    def touches(self, other: "Mover") -> bool:
        """Tell whether other is less than half a cell away."""
        (x1, y1), (x2, y2) = self.position, other.position
        return abs(x1 - x2) + abs(y1 - y2) < 0.5

    def update(self, maze: list[list[int]],
               dt: float) -> list[tuple[int, int]]:
        """Move speed * dt cells along the corridors.

        At each cell centre, choose_direction() decides where to go next,
        and None stops the mover.

        Returns:
            The cells reached during this move, in order: usually none or
            one, several only if the frame took very long.
        """
        reached: list[tuple[int, int]] = []
        distance = self.speed * dt
        while distance > 0:
            if self.progress == 0:
                self.direction = self.choose_direction(maze)
            if self.direction is None:
                break
            self.facing = self.direction
            remaining = 1 - self.progress
            if distance < remaining:
                self.progress += distance
                break
            distance -= remaining
            self.cell = neighbour(self.cell, self.direction)
            self.progress = 0.0
            reached.append(self.cell)
        return reached

    @abstractmethod
    def choose_direction(self, maze: list[list[int]]) -> str | None:
        """Return the direction to take from a cell centre, or None."""
