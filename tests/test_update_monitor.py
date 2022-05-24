from pytest import MonkeyPatch
import pytest

from src.update_monitor import (
    get_current_packages,
    get_new_available,
    get_repo_packages,
    VersionFilters,
)

import json

def test_get_packages(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("shutil.which", lambda _: "123")
    def create_process_mock(*args, **kwargs):
        class Stdout:
            def readlines(self):
                return [b"linux 1.0.0", b"python3 3.10.4"]
        class ProcessMocked:
            def __init__(self):
                self.stdout = Stdout()
        return ProcessMocked()

    monkeypatch.setattr("subprocess.Popen", create_process_mock)
    assert get_current_packages() == {"linux": "1.0.0", "python3": "3.10.4"}

def test_get_packages_no_pacman(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(FileNotFoundError):
        get_current_packages()

def test_get_repo_packages(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("src.update_monitor.SCRIPT_DIR", ".")    
    actual = get_repo_packages(["tests/files/core.db"])
    with open("tests/files/core_expected.json", "r") as f:
        expected = json.load(f)
    assert actual == expected

@pytest.mark.parametrize(
    "current,newest,version,expected",
    [
        [{
            "linux": "1.0.0",
            "neovim": "0.7.0",
            "python3": "3.10.4"
         },
         {
            "linux": "2.0.0",
            "neovim": "0.8.0",
            "python3": "3.10.5"
         },
         VersionFilters.Major,
         [("linux", "1.0.0", "2.0.0")]
        ],
        [{
            "linux": "1.0.0",
            "neovim": "0.7.0",
            "python3": "3.10.4"
         },
         {
            "linux": "2.0.0",
            "neovim": "0.8.0",
            "python3": "3.10.5"
         },
         VersionFilters.Minor,
         [("linux", "1.0.0", "2.0.0"), ("neovim", "0.7.0", "0.8.0")]
        ],
        [{
            "linux": "1.0.0",
            "neovim": "0.7.0",
            "python3": "3.10.4"
         },
         {
            "linux": "2.0.0",
            "neovim": "0.8.0",
            "python3": "3.10.5"
         },
         VersionFilters.Micro,
         [("linux", "1.0.0", "2.0.0"), ("neovim", "0.7.0", "0.8.0"), ("python3", "3.10.4", "3.10.5")]
        ],
        [{
            "linux": "1.0.0",
            "neovim": "0.7.0",
            "python3": "3.10.4"
         },
         {
            "linux": "2.0.0",
            "neovim": "0.8.0",
            "python3": "3.10.5"
         },
         VersionFilters.All,
         [("linux", "1.0.0", "2.0.0"), ("neovim", "0.7.0", "0.8.0"), ("python3", "3.10.4", "3.10.5")]
        ],
        [{
            "linux": "1.0.0",
            "neovim": "0.7.0",
            "python3": "3.10.4"
         },
         {
            "linux": "1.0.0",
            "neovim": "0.7.0",
            "python3": "3.10.4"
         },
         VersionFilters.All,
         []
        ],
        [{
            "some-weird-versioning": "2022-abcde",
         },
         {
            "some-weird-versioning": "2022-abcdef",
         },
         VersionFilters.Major,
         [("some-weird-versioning", "2022-abcde", "2022-abcdef")]
        ]
    ],
    ids=lambda x: x
)
def test_get_new_available_major(current, newest, version, expected):
    actual = get_new_available(current, newest, version)
    assert actual == expected

