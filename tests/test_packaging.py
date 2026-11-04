"""Tests for the downloadable app (make package): paths and arguments."""
import importlib
import sys
from pathlib import Path
from typing import Any

import pytest

from src import constants
from src.constants import (APP_NAME, FONT, LOGO, frozen, resource_path,
                           user_data_path)

ROOT = Path(__file__).resolve().parent.parent
pacman_module = importlib.import_module("pac-man")


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record the config file main() starts the game with, without a window.
    """
    configs: list[str] = []
    monkeypatch.setattr(pacman_module, "Pacman", configs.append)
    return configs


def as_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend to run inside the app, as PyInstaller's launcher sets it."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)


def test_not_frozen_by_default() -> None:
    """A plain python run never has sys.frozen."""
    assert not frozen()


def test_resources_found_from_any_folder(monkeypatch: pytest.MonkeyPatch,
                                         tmp_path: Path) -> None:
    """Outside the app, the files are found in the project folder."""
    monkeypatch.chdir(tmp_path)
    assert resource_path("config.json") == str(ROOT / "config.json")
    assert Path(FONT).is_file() and Path(LOGO).is_file()


def test_resources_inside_the_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inside the app, the files are in the folder it unpacked them to."""
    monkeypatch.setattr(sys, "_MEIPASS", "/unpacked", raising=False)
    assert resource_path("config.json") == str(Path("/unpacked/config.json"))


@pytest.mark.parametrize("platform, folder", [
    ("darwin", "Library/Application Support"), ("linux", ".local/share")])
def test_user_data_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                          platform: str, folder: str) -> None:
    """The app keeps the scores in the user's data folder."""
    monkeypatch.setattr(constants.sys, "platform", platform)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert user_data_path("data/leaderboard.json") == str(
        tmp_path / folder / APP_NAME / "leaderboard.json")


def test_user_data_keeps_absolute_paths() -> None:
    """An absolute highscore_filename is used as it is."""
    assert user_data_path("/scores/mine.json") == "/scores/mine.json"


def test_terminal_without_argument_fails(
        monkeypatch: pytest.MonkeyPatch, started: list[str]) -> None:
    """From the terminal, the config file is still required."""
    monkeypatch.setattr(sys, "argv", ["pac-man.py"])
    with pytest.raises(SystemExit):
        pacman_module.main()
    assert started == []


def test_terminal_with_argument(monkeypatch: pytest.MonkeyPatch,
                                started: list[str]) -> None:
    """From the terminal, the given config file is used."""
    monkeypatch.setattr(sys, "argv", ["pac-man.py", "config.json"])
    pacman_module.main()
    assert started == ["config.json"]


@pytest.mark.parametrize("argv", [[], ["-psn_0_12345"]])
def test_app_uses_its_config(monkeypatch: pytest.MonkeyPatch,
                             started: list[str], argv: list[str]) -> None:
    """A double-click (no argument, or macOS' -psn one) uses the bundled
    config.json."""
    as_app(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["Pacman42", *argv])
    pacman_module.main()
    assert started == [resource_path("config.json")]


def test_app_accepts_another_config(monkeypatch: pytest.MonkeyPatch,
                                    started: list[str]) -> None:
    """The app started from a terminal can still be given a config file."""
    as_app(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["Pacman42", "my.json"])
    pacman_module.main()
    assert started == ["my.json"]


def test_app_saves_scores_for_the_user(monkeypatch: pytest.MonkeyPatch,
                                       tmp_path: Path) -> None:
    """Inside the app, a new player starts with an empty leaderboard kept
    in their own data folder."""
    as_app(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setattr(pacman_module.Pacman, "_run", lambda self: None)
    program: Any = pacman_module.Pacman(str(ROOT / "config.json"))
    assert program.scores.fetch_entries() == []
    assert program.scores.add_entry("NEW", 100)
    saved = list(tmp_path.rglob("leaderboard.json"))
    assert len(saved) == 1 and APP_NAME in str(saved[0])
