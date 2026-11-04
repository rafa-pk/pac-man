"""Tests for src/parser.py, one per rule of the README "Configuration"."""
from pathlib import Path
from typing import Callable

import pytest

from src.parser import DEFAULT_LEVELS, Config, Parser

ROOT = Path(__file__).resolve().parent.parent
WriteConfig = Callable[[str], str]
Capture = pytest.CaptureFixture[str]


def sizes(config: Config) -> list[tuple[int, int]]:
    """Return the levels of config as (width, height) pairs."""
    return [(level.width, level.height) for level in config.levels]


# --- the shipped file -------------------------------------------------------

def test_shipped_config_is_the_default_one(capsys: Capture) -> None:
    """config.json loads without any warning and equals the defaults."""
    config = Parser.get_config(str(ROOT / "config.json"))
    assert capsys.readouterr().err == ""
    assert config == Config()


# --- unusable files: whole default configuration ----------------------------

def test_missing_file(tmp_path: Path, capsys: Capture) -> None:
    """A missing file gives the default configuration."""
    config = Parser.get_config(str(tmp_path / "nope.json"))
    assert config == Config()
    assert "cannot read" in capsys.readouterr().err


def test_directory_instead_of_file(tmp_path: Path, capsys: Capture) -> None:
    """A directory gives the default configuration."""
    assert Parser.get_config(str(tmp_path)) == Config()
    assert "cannot read" in capsys.readouterr().err


@pytest.mark.parametrize("content, message", [
    ('{"lives": 4,}', "not valid JSON"),
    ("", "not valid JSON"),
    ("[1, 2]", "must contain a JSON object"),
    ('{"lives": 1' + "0" * 5000 + "}", "cannot be decoded"),
])
def test_unusable_content(write_config: WriteConfig, capsys: Capture,
                          content: str, message: str) -> None:
    """Broken JSON, a list or a giant number give the default config."""
    assert Parser.get_config(write_config(content)) == Config()
    assert message in capsys.readouterr().err


def test_binary_file(tmp_path: Path, capsys: Capture) -> None:
    """A file that is not UTF-8 text gives the default configuration."""
    path = tmp_path / "config.json"
    path.write_bytes(b"\xff\xfe\x00")
    assert Parser.get_config(str(path)) == Config()
    assert "cannot be decoded" in capsys.readouterr().err


# --- comments ---------------------------------------------------------------

def test_comment_lines_are_ignored(write_config: WriteConfig) -> None:
    """Lines starting with '#', even indented, are ignored."""
    content = '{\n# comment\n    # indented comment\n    "lives": 5\n}'
    assert Parser.get_config(write_config(content)).lives == 5


def test_error_line_number_counts_comments(write_config: WriteConfig,
                                           capsys: Capture) -> None:
    """A JSON error is reported at its real line, comments included."""
    content = '{\n  # comment\n  "lives": 3\n  "seed": 42\n}'
    Parser.get_config(write_config(content))
    assert "line 4" in capsys.readouterr().err


# --- keys -------------------------------------------------------------------

def test_unknown_key_is_ignored(write_config: WriteConfig,
                                capsys: Capture) -> None:
    """An unknown key changes nothing and is reported."""
    assert Parser.get_config(write_config('{"speed": 3}')) == Config()
    assert 'unknown key "speed" ignored' in capsys.readouterr().err


def test_missing_key_uses_its_default(write_config: WriteConfig,
                                      capsys: Capture) -> None:
    """A missing key keeps its default value and is reported."""
    config = Parser.get_config(write_config('{"lives": 5}'))
    assert config.pacgum == 42
    assert '"pacgum" is missing' in capsys.readouterr().err


@pytest.mark.parametrize("value", ['"300"', "300.5", "true", "null", "[3]"])
def test_wrong_type_uses_the_default(write_config: WriteConfig,
                                     capsys: Capture, value: str) -> None:
    """Only real JSON integers are accepted ("300", 300.5, true...)."""
    content = f'{{"points_per_ghost": {value}}}'
    config = Parser.get_config(write_config(content))
    assert config.points_per_ghost == 200
    assert '"points_per_ghost" is invalid' in capsys.readouterr().err


@pytest.mark.parametrize("key, value, expected", [
    ("lives", 1, 3),
    ("lives", 100, 9),
    ("pacgum", 0, 1),
    ("points_per_pacgum", -5, 0),
    ("points_per_ghost", 99999, 10_000),
    ("seed", 0, 1),
    ("level_max_time", 1, 10),
    ("level_max_time", 100_000, 600),
])
def test_out_of_range_is_clamped(write_config: WriteConfig, capsys: Capture,
                                 key: str, value: int, expected: int) -> None:
    """An integer outside its range becomes the nearest limit."""
    config = Parser.get_config(write_config(f'{{"{key}": {value}}}'))
    assert getattr(config, key) == expected
    assert f'"{key}" = {value} is' in capsys.readouterr().err


def test_one_bad_key_keeps_the_others(write_config: WriteConfig) -> None:
    """An invalid value only affects its own key."""
    config = Parser.get_config(write_config('{"lives": 1, "seed": 7}'))
    assert (config.lives, config.seed) == (3, 7)


@pytest.mark.parametrize("value, expected", [
    ('"scores.json"', "scores.json"),
    ('"pac-man.py"', "data/leaderboard.json"),
    ("42", "data/leaderboard.json"),
])
def test_highscore_filename(write_config: WriteConfig, value: str,
                            expected: str) -> None:
    """The highscore file must be a name ending in .json."""
    content = f'{{"highscore_filename": {value}}}'
    assert Parser.get_config(write_config(content)).highscore_filename \
        == expected


# --- levels -----------------------------------------------------------------

def test_levels_not_a_list(write_config: WriteConfig,
                           capsys: Capture) -> None:
    """levels must be a list, otherwise the default levels are used."""
    config = Parser.get_config(write_config('{"levels": "abc"}'))
    assert sizes(config) == DEFAULT_LEVELS
    assert '"levels" must be a list' in capsys.readouterr().err


def test_level_sizes_are_clamped(write_config: WriteConfig) -> None:
    """Each level dimension is limited to 5..50."""
    content = '{"levels": [{"width": 2, "height": 60}]}'
    assert sizes(Parser.get_config(write_config(content)))[0] == (5, 50)


def test_invalid_levels_are_ignored(write_config: WriteConfig,
                                    capsys: Capture) -> None:
    """Invalid entries are skipped, then defaults complete the list."""
    content = ('{"levels": [{"width": 20, "height": 12}, [15, 15], '
               '{"width": "9", "height": 9}, {"width": 20}]}')
    config = Parser.get_config(write_config(content))
    assert sizes(config) == [(20, 12)] + DEFAULT_LEVELS[1:]
    errors = capsys.readouterr().err
    for number in (2, 3, 4):
        assert f"level {number}" in errors
    assert "only 1 valid level(s)" in errors


def test_more_than_ten_levels_are_kept(write_config: WriteConfig) -> None:
    """There is no maximum number of levels."""
    levels = ", ".join(['{"width": 7, "height": 7}'] * 12)
    config = Parser.get_config(write_config(f'{{"levels": [{levels}]}}'))
    assert sizes(config) == [(7, 7)] * 12
