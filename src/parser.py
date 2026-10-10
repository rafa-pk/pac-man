import json
import re
from typing import Any, List
from pydantic import BaseModel, Field


class Config(BaseModel):

    highscore_filename: str
    levels: List[List[int]]
    lives: int = Field(ge=3)
    pacgum: int
    points_per_pacgum: int
    points_per_super_pacgum: int
    points_per_ghost: int
    seed: int
    level_max_time: int


class Parser:

    def get_config(config_file: str) -> dict[str, Any]:
        
        try:
            with open(config_file, 'r') as file:
                lines = []
                for line in file:
                    if line.strip().startswith("#"):
                        continue
                    lines.append(line)
            config = json.loads("".join(lines))
            return Config(**config)
        except Exception as error:
            print(f"Parsing Error: Config file is not valid or could not be opened: {error}.")
            print("Defaulting to default configuration.")
            # return Config(default)