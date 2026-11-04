"""Tests for src/game/scores.py: the top 10 never stops the game."""
import json
from pathlib import Path

import pytest

from src.game.scores import Scores

ROOT = Path(__file__).resolve().parent.parent
Capture = pytest.CaptureFixture[str]


def write(path: Path, content: object) -> str:
    """Write content as JSON in path and return the path as a string."""
    path.write_text(json.dumps(content), encoding="utf-8")
    return str(path)


def test_shipped_leaderboard_is_valid(capsys: Capture) -> None:
    """The provided file loads its 10 best scores without a warning."""
    scores = Scores(str(ROOT / "data" / "leaderboard.json"))
    assert len(scores.fetch_entries()) == 10
    assert capsys.readouterr().err == ""


def test_missing_file_means_no_score_yet(tmp_path: Path) -> None:
    """No file: no score, and a second start still works."""
    path = str(tmp_path / "scores.json")
    assert Scores(path).fetch_entries() == []
    assert Scores(path).fetch_entries() == []


@pytest.mark.parametrize("content", [b"", b"{", b"\xff\xfe", b"[1, 2]",
                                     b'{"leaderboard": 5}'])
def test_broken_file_is_reported_not_fatal(tmp_path: Path, capsys: Capture,
                                           content: bytes) -> None:
    """Empty, broken, binary or badly shaped: a warning and no score."""
    path = tmp_path / "scores.json"
    path.write_bytes(content)
    assert Scores(str(path)).fetch_entries() == []
    assert "Highscores:" in capsys.readouterr().err


def test_invalid_entries_are_skipped(tmp_path: Path, capsys: Capture) -> None:
    """Names of 1 to 10 letters, digits or spaces; integer scores >= 0."""
    path = write(tmp_path / "scores.json", {"leaderboard": [
        {"name": "ok 42", "score": 10},
        {"name": "elevenchars", "score": 10},
        {"name": "bad-char", "score": 10},
        {"name": "", "score": 10},
        {"name": "text", "score": "10"},
        {"name": "negative", "score": -1},
        {"name": "boolean", "score": True},
        {"name": "float", "score": 1.5},
        "not a dict"]})
    assert Scores(path).fetch_entries() == [{"name": "ok 42", "score": 10}]
    assert "8 invalid entries" in capsys.readouterr().err


def test_loaded_scores_are_sorted_and_cut_to_10(tmp_path: Path) -> None:
    """The best score comes first, and only the 10 best are kept."""
    path = write(tmp_path / "scores.json", {"leaderboard": [
        {"name": f"p{score}", "score": score} for score in range(12)]})
    loaded = [entry["score"] for entry in Scores(path).fetch_entries()]
    assert loaded == list(range(11, 1, -1))


def test_added_score_is_saved(tmp_path: Path) -> None:
    """The next game loads the new score; the folder is created."""
    path = str(tmp_path / "new" / "scores.json")
    assert Scores(path).add_entry("amine", 4200)
    assert Scores(path).fetch_entries() == [{"name": "amine", "score": 4200}]


def test_an_11th_score_pushes_out_the_lowest(tmp_path: Path) -> None:
    """Only the 10 best scores are kept, best first."""
    scores = Scores(str(tmp_path / "scores.json"))
    for score in range(11):
        scores.add_entry("p", score)
    kept = [entry["score"] for entry in scores.fetch_entries()]
    assert kept == list(range(10, 0, -1))


@pytest.mark.parametrize("name, score", [("elevenchars", 1), ("a-b", 1),
                                         ("", 1), ("ok", -5)])
def test_invalid_score_is_refused(tmp_path: Path, name: str,
                                  score: int) -> None:
    """A bad name or a negative score is refused; nothing is written."""
    path = tmp_path / "scores.json"
    assert not Scores(str(path)).add_entry(name, score)
    assert not path.exists()


def test_unwritable_file_is_reported_not_fatal(tmp_path: Path,
                                               capsys: Capture) -> None:
    """A folder in place of the file: warnings, but the game goes on."""
    scores = Scores(str(tmp_path))
    assert scores.add_entry("amine", 10)
    assert "could not be saved" in capsys.readouterr().err
