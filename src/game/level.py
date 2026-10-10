from mazegenerator.mazegenerator import MazeGenerator
from src.parser import Config
from src.gui import GUI
import random


class Level:

    def __init__(self, dimensions: list[int], config: Config, seed: random.Random) -> None:

        self.dimensions = dimensions
        self.seed = seed
        self.generator = MazeGenerator(size=(dimensions[0], dimensions[1]), seed=self.seed)
        self.maze = self.generator.maze
        self.corners = [(0, 0), (self.dimensions[0] - 1, 0), (0, self.dimensions[1] - 1), (self.dimensions[0] - 1, self.dimensions[1] - 1)]
        self.logo = [(x, y) for y, row in enumerate(self.maze) for x, cell in enumerate(row) if cell == 15]
        self.pacgums = self._place_pacgums(config.pacgum)
        self.available_pacgums = self.pacgums
        self.super_pacgums = set(self.corners)
        self.available_super_pacgums = self.super_pacgums
        self.player = Player()

    # def _place_player(self)

    def _place_pacgums(self, pacgums: int) -> set[tuple[int, int]]:

        excluded = {*self.corners, *self.logo}
        
        candidates = [
            (x, y)
            for y in range(self.dimensions[1])
            for x in range(self.dimensions[0])
            if (x, y) not in excluded
        ]
        count = min(pacgums, len(candidates))
        if count == 0:
            return set()
        step = len(candidates) / count
        return {candidates[int(i * step)] for i in range(count)}