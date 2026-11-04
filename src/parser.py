"""Load and validate the game configuration file.

The rules (types, defaults, ranges, error handling) are the ones documented in
the "Configuration" section of the README: keep both in sync.
"""
import json
import sys
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_core import ErrorDetails

MIN_LEVELS = 10
# (width, height) of the default levels: the same as the shipped config.json.
DEFAULT_LEVELS = [(15, 15), (10, 10), (5, 5), (20, 20), (25, 25),
                  (18, 18), (42, 42), (15, 15), (20, 20), (42, 42)]
# pydantic error type -> (name of the limit in the error context, message)
RANGE_ERRORS = {
    "greater_than_equal": ("ge", "below the minimum"),
    "less_than_equal": ("le", "above the maximum"),
}


class LevelSize(BaseModel):
    """Size of one maze, in cells."""

    width: int = Field(strict=True, ge=5, le=50)
    height: int = Field(strict=True, ge=5, le=50)


def default_levels() -> list[LevelSize]:
    """Return a new list holding the default levels."""
    return [LevelSize(width=w, height=h) for w, h in DEFAULT_LEVELS]


class Config(BaseModel):
    """Game settings: the README "Configuration" table, written as code."""

    model_config = ConfigDict(validate_assignment=True)

    highscore_filename: str = Field(
        default="data/leaderboard.json", strict=True, pattern=r"\.json$")
    levels: list[LevelSize] = Field(default_factory=default_levels)
    lives: int = Field(default=3, strict=True, ge=3, le=9)
    pacgum: int = Field(default=42, strict=True, ge=1)
    points_per_pacgum: int = Field(default=10, strict=True, ge=0, le=10_000)
    points_per_super_pacgum: int = Field(
        default=50, strict=True, ge=0, le=10_000)
    points_per_ghost: int = Field(default=200, strict=True, ge=0, le=10_000)
    seed: int = Field(default=42, strict=True, ge=1)
    level_max_time: int = Field(default=90, strict=True, ge=10, le=600)


class Parser:
    """Build a Config from the file given on the command line."""

    @staticmethod
    def get_config(path: str) -> Config:
        """Load the configuration file without ever raising.

        Each key is checked on its own: an invalid value only replaces that
        key, and every correction is reported on stderr.

        Args:
            path: Path of the JSON configuration file.

        Returns:
            The validated configuration.
        """
        config = Config()
        data = _load_json(path)
        if data is None:
            return config
        for key, value in data.items():
            if key not in Config.model_fields:
                _warn(f'unknown key "{key}" ignored.')
            elif key == "levels":
                config.levels = _read_levels(value)
            else:
                _set(config, key, value)
        for key in Config.model_fields:
            if key not in data:
                _warn(f'"{key}" is missing, using its default value.')
        return config


def _warn(message: str) -> None:
    """Print one configuration warning on stderr."""
    print(f"Config: {message}", file=sys.stderr)


def _load_json(path: str) -> dict[str, Any] | None:
    """Read the file, ignore '#' comment lines and parse the JSON.

    Comment lines are replaced by empty lines instead of being removed, so
    the line numbers given in JSON error messages still match the file.

    Returns:
        The top-level JSON object, or None if the file is unusable.
    """
    try:
        with open(path, encoding="utf-8") as file:
            lines = ["\n" if line.lstrip().startswith("#") else line
                     for line in file]
        data = json.loads("".join(lines))
    except OSError as error:
        _warn(f"cannot read '{path}' ({error.strerror}), "
              "using the default configuration.")
        return None
    except json.JSONDecodeError as error:
        _warn(f"'{path}' is not valid JSON (line {error.lineno}, column "
              f"{error.colno}: {error.msg}), using the default configuration.")
        return None
    except ValueError:  # not UTF-8 text, or a number too long to convert
        _warn(f"'{path}' cannot be decoded, using the default configuration.")
        return None
    if not isinstance(data, dict):
        _warn(f"'{path}' must contain a JSON object {{...}}, "
              "using the default configuration.")
        return None
    return data


def _range_fix(problem: ErrorDetails) -> tuple[str, int] | None:
    """Return (message, limit) if a value crossed its minimum or maximum.

    Args:
        problem: One error reported by pydantic.

    Returns:
        None when the error is about something else (type, format...).
    """
    rule = RANGE_ERRORS.get(problem["type"])
    if rule is None:
        return None
    limit_name, text = rule
    return text, problem["ctx"][limit_name]


def _set(config: Config, key: str, value: Any) -> None:
    """Assign one key of config, letting pydantic check the value.

    An integer outside its range becomes the nearest limit; any other
    invalid value leaves the default in place.
    """
    try:
        setattr(config, key, value)
    except ValidationError as error:
        problem = error.errors()[0]
        fix = _range_fix(problem)
        if fix is None:
            _warn(f'"{key}" is invalid ({problem["msg"]}), using '
                  f"{json.dumps(getattr(config, key))}.")
            return
        text, limit = fix
        _warn(f'"{key}" = {value} is {text} ({limit}), using {limit}.')
        setattr(config, key, limit)


def _read_levels(value: Any) -> list[LevelSize]:
    """Return the valid levels, completed with defaults up to MIN_LEVELS."""
    if not isinstance(value, list):
        _warn('"levels" must be a list, using the default levels.')
        return default_levels()
    levels = []
    for number, entry in enumerate(value, start=1):
        level = _read_level(number, entry)
        if level is not None:
            levels.append(level)
    if len(levels) < MIN_LEVELS:
        _warn(f"only {len(levels)} valid level(s), adding default levels "
              f"to reach {MIN_LEVELS}.")
        levels += default_levels()[len(levels):]
    return levels


def _read_level(number: int, entry: Any) -> LevelSize | None:
    """Return one level with its sizes clamped, or None if it is invalid."""
    if not isinstance(entry, dict):
        _warn(f'level {number} is not {{"width": ..., "height": ...}}, '
              "level ignored.")
        return None
    fixed = dict(entry)
    try:
        return LevelSize(**entry)
    except ValidationError as error:
        for problem in error.errors():
            name = problem["loc"][0]
            fix = _range_fix(problem)
            if fix is None:
                _warn(f'level {number} "{name}" is invalid '
                      f'({problem["msg"]}), level ignored.')
                return None
            text, limit = fix
            _warn(f'level {number} "{name}" = {entry[name]} is {text} '
                  f"({limit}), using {limit}.")
            fixed[name] = limit
    return LevelSize(**fixed)
