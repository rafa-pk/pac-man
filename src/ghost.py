"""The ghosts: at each crossing, they take the shortest way to a target."""
import random

from src.mover import DIRECTIONS, OPPOSITE, Mover, can_move, neighbour
from src.pathfinding import distances_from
from src.player import BASE_SPEED, Player

GHOST_SPEED_RATIO = 0.9  # ghosts move at 90 % of Pac-Man's speed
# Order used to break ties between equally good ways, as in the arcade game.
PRIORITY = ("up", "left", "down", "right")
FRIGHT_TIME = 6.0  # seconds a super-pacgum makes the ghosts edible
FRIGHT_SPEED_RATIO = 0.5  # edible ghosts move at half their speed
RESPAWN_DELAY = 5.0  # an eaten ghost is out of the game at least this long
EYES_SPEED_RATIO = 2.0  # the eyes of an eaten ghost go home twice as fast


class Ghost(Mover):
    """A ghost: goes towards its target cell along the corridors.

    At each crossing it takes the way whose next cell is the closest to the
    target, distances being counted along the corridors (breadth-first
    search). It never turns back on its own, except in a dead end.
    After a super-pacgum it is edible for a while: it runs away instead,
    at half speed. Once eaten, only its eyes are left: they go back to its
    corner, where the ghost revives.
    """

    def __init__(self, name: str, corner: tuple[int, int],
                 speed: float = GHOST_SPEED_RATIO * BASE_SPEED) -> None:
        """Create a ghost waiting in its corner.

        Args:
            name: Name of the ghost, which also selects its color.
            corner: Starting cell (x, y), where it respawns.
            speed: Speed in cells per second.
        """
        super().__init__(corner, speed)
        self.name = name
        self.target = corner
        self.fright_time = 0.0  # seconds left as an edible ghost
        self.eaten = False  # eaten: only its eyes are left, going home
        self.respawn_time = 0.0  # seconds left before an eaten one revives

    @property
    def edible(self) -> bool:
        """Tell whether Pac-Man can eat the ghost (after a super-pacgum)."""
        return self.fright_time > 0

    @property
    def home(self) -> bool:
        """Tell whether the ghost stands on its corner, at the cell centre."""
        return self.cell == self.start_position and self.progress == 0

    def chase(self, player: Player, maze: list[list[int]]) -> None:
        """Aim at the cell of Pac-Man: Blinky's way of chasing.

        The other ghosts override this method; some of them need the maze.
        """
        self.target = player.cell

    def flee(self, player: Player) -> None:
        """Aim at Pac-Man, to run away from it (see choose_direction)."""
        self.target = player.cell

    def frighten(self) -> None:
        """Become edible for FRIGHT_TIME seconds, unless already eaten."""
        if not self.eaten:
            self.fright_time = FRIGHT_TIME

    def get_eaten(self) -> None:
        """Turn into eyes that go back to the corner, out of the game."""
        self.fright_time = 0.0
        self.eaten = True
        self.respawn_time = RESPAWN_DELAY
        self.target = self.start_position

    def respawn(self) -> None:
        """Go back to its corner, dangerous again."""
        super().respawn()
        self.fright_time = self.respawn_time = 0.0
        self.eaten = False

    def update(self, maze: list[list[int]],
               dt: float) -> list[tuple[int, int]]:
        """Count down the fright or the time away, then move.

        An edible ghost moves at half speed. The eyes of an eaten one go
        back to its corner at EYES_SPEED_RATIO times its speed and wait
        there: it revives once RESPAWN_DELAY seconds have passed since it
        was eaten.
        """
        if self.eaten:
            self.respawn_time = max(0.0, self.respawn_time - dt)
            if self.respawn_time == 0 and self.home:
                self.eaten = False  # revives in its corner
                return []
            return super().update(maze, dt * EYES_SPEED_RATIO)
        self.fright_time = max(0.0, self.fright_time - dt)
        if self.edible:
            dt *= FRIGHT_SPEED_RATIO  # half the time: half the way
        return super().update(maze, dt)

    def open_ways(self, maze: list[list[int]]) -> list[str]:
        """Return the open ways, without turning back unless in a dead end."""
        back = OPPOSITE[self.direction] if self.direction else None
        ways = [way for way in PRIORITY
                if way != back and can_move(maze, self.cell, way)]
        if not ways:  # dead end: turning back is the only way out
            ways = [way for way in PRIORITY if can_move(maze, self.cell, way)]
        return ways

    def choose_direction(self, maze: list[list[int]]) -> str | None:
        """Take the open way whose next cell is the closest to the target."""
        if self.eaten and self.home:
            return None  # the eyes wait in the corner
        ways = self.open_ways(maze)
        if not ways:
            return None
        distances = distances_from(maze, self.target)
        too_far = len(maze) * len(maze[0])  # longer than any real path

        def distance(way: str) -> int:
            """Return the steps from the cell after way to the target."""
            return distances.get(neighbour(self.cell, way), too_far)
        if self.edible:  # run away: the way farthest from Pac-Man
            return max(ways, key=distance)
        return min(ways, key=distance)


PINKY_LEAD = 4  # Pinky aims this many cells ahead of Pac-Man


class Pinky(Ghost):
    """Pinky ambushes: it aims ahead of Pac-Man to cut it off."""

    def chase(self, player: Player, maze: list[list[int]]) -> None:
        """Aim PINKY_LEAD cells ahead of Pac-Man, as the crow flies.

        Walls are ignored, as in the arcade game, so the target is often
        on the other side of a wall and Pinky takes another way than
        Blinky. The target is kept inside the grid; if it falls in the
        closed "42" cells, Pinky aims at Pac-Man instead.
        """
        dx, dy, _ = DIRECTIONS[player.facing]
        x = min(max(player.cell[0] + PINKY_LEAD * dx, 0), len(maze[0]) - 1)
        y = min(max(player.cell[1] + PINKY_LEAD * dy, 0), len(maze) - 1)
        self.target = (x, y) if maze[y][x] != 15 else player.cell


INKY_RANDOMNESS = 0.5  # Inky takes a random way at half of the crossings


class Inky(Ghost):
    """Inky is unpredictable: at many crossings it takes a random way."""

    def __init__(self, name: str, corner: tuple[int, int],
                 speed: float = GHOST_SPEED_RATIO * BASE_SPEED) -> None:
        """Create Inky with its own random generator.

        Not the random module: the maze package reseeds it with the fixed
        seed of level 1, so Inky would make the same moves in every game.
        """
        super().__init__(name, corner, speed)
        self.rng = random.Random()

    def choose_direction(self, maze: list[list[int]]) -> str | None:
        """Take a random way INKY_RANDOMNESS of the time, else chase.

        An edible ghost runs away and eaten eyes go home: never at random.
        """
        if (self.edible or self.eaten
                or self.rng.random() >= INKY_RANDOMNESS):
            return super().choose_direction(maze)
        ways = self.open_ways(maze)
        return self.rng.choice(ways) if ways else None


def free_cells(maze: list[list[int]]) -> list[tuple[int, int]]:
    """Return every cell of maze but the closed "42" ones, row by row."""
    return [(x, y) for y, row in enumerate(maze)
            for x, cell in enumerate(row) if cell != 15]


class Clyde(Ghost):
    """Clyde wanders: at each crossing it heads for a new random cell."""

    def __init__(self, name: str, corner: tuple[int, int],
                 speed: float = GHOST_SPEED_RATIO * BASE_SPEED) -> None:
        """Create Clyde with its own random generator.

        Not the random module: the maze package reseeds it with the fixed
        seed of level 1, so Clyde would make the same moves in every game.
        """
        super().__init__(name, corner, speed)
        self.rng = random.Random()

    def chase(self, player: Player, maze: list[list[int]]) -> None:
        """Keep the target drawn at the last crossing: Clyde ignores
        Pac-Man (choose_direction draws the next one)."""

    def choose_direction(self, maze: list[list[int]]) -> str | None:
        """At a crossing, draw a new target cell, then take the shortest
        way there; in a corridor, keep going to the same target.

        A crossing is a cell with more than one way forward. An edible
        ghost runs away and eaten eyes go home: never a random target.
        Closed "42" cells are never drawn, since no way leads into them.
        """
        if (not self.edible and not self.eaten
                and len(self.open_ways(maze)) > 1):
            self.target = self.rng.choice(free_cells(maze))
        return super().choose_direction(maze)
