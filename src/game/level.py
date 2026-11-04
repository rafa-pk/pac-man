from mazegenerator.mazegenerator import MazeGenerator
from src.ghost import Clyde, Ghost, Inky, Pinky
from src.player import Player
from src.parser import Config, LevelSize
import sys

# The maze package draws a random maze for any seed <= 0.
RANDOM_SEED = 0


class Level:

    def __init__(self, size: LevelSize, config: Config, seed: int) -> None:

        self.dimensions = (size.width, size.height)
        self.seed = seed
        self.config = config
        self.generator = self._generate()
        self.maze = self.generator.maze
        self.corners = [(0, 0), (self.dimensions[0] - 1, 0), (0, self.dimensions[1] - 1), (self.dimensions[0] - 1, self.dimensions[1] - 1)]
        self.logo = [(x, y) for y, row in enumerate(self.maze) for x, cell in enumerate(row) if cell == 15]
        self.player_start = self._find_maze_center()
        self.pacgums = self._place_pacgums(config.pacgum)
        self.available_pacgums = set(self.pacgums)
        self.super_pacgums = set(self.corners)
        self.available_super_pacgums = set(self.super_pacgums)
        self.player = Player(self.player_start)
        self.ghosts = [Ghost("blinky", self.corners[1]),
                       Pinky("pinky", self.corners[0]),
                       Inky("inky", self.corners[3]),
                       Clyde("clyde", self.corners[2])]

    def eat(self, cell: tuple[int, int]) -> int:
        """Eat what lies on cell; return the points it gives (0 if none)."""
        if cell in self.available_pacgums:
            self.available_pacgums.remove(cell)
            return self.config.points_per_pacgum
        if cell in self.available_super_pacgums:
            self.available_super_pacgums.remove(cell)
            return self.config.points_per_super_pacgum
        return 0

    @property
    def cleared(self) -> bool:
        """Tell whether every pacgum and super-pacgum has been eaten."""
        return not self.available_pacgums and not self.available_super_pacgums

    # def _place_player(self)

    def _generate(self) -> MazeGenerator:
        """Run the external maze package, stopping cleanly if it fails."""
        try:
            return MazeGenerator(size=self.dimensions, seed=self.seed)
        except Exception as error:  # external code: any failure is possible
            print(f"Error: the maze generator failed for a "
                  f"{self.dimensions[0]}x{self.dimensions[1]} maze ({error}).",
                  file=sys.stderr)
            sys.exit(1)

    def _place_pacgums(self, pacgums: int) -> set[tuple[int, int]]:

        excluded = {*self.corners, *self.logo, self.player_start}
        
        candidates = [
            (x, y)
            for y in range(self.dimensions[1])
            for x in range(self.dimensions[0])
            if (x, y) not in excluded
        ]
        count = min(pacgums, len(candidates))
        if count < pacgums:
            print(f"Config: a {self.dimensions[0]}x{self.dimensions[1]} maze "
                  f"has room for {count} pacgums, placing {count} instead "
                  f"of {pacgums}.", file=sys.stderr)
        if count == 0:
            return set()
        step = len(candidates) / count
        return {candidates[int(i * step)] for i in range(count)}

    def _find_maze_center(self) -> tuple[int, int]:
        """Return the free cell closest to the middle of the maze.

        The exact middle can be a cell of the "42" pattern, which is closed.
        """
        middle_x, middle_y = self.dimensions[0] // 2, self.dimensions[1] // 2
        free = [(x, y) for y in range(self.dimensions[1])
                for x in range(self.dimensions[0]) if (x, y) not in self.logo]
        return min(free, key=lambda cell: abs(cell[0] - middle_x)
                   + abs(cell[1] - middle_y))
