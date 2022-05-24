from pytest import MonkeyPatch
import pytest

from src.update_monitor import (
    get_current_packages,
    get_new_available,
    get_repo_packages,
    construct_html,
    VersionFilters,
)

import json
import tarfile

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

def test_get_repo_packages_no_file():
    with pytest.raises(FileNotFoundError):
        get_repo_packages(["some/path/core.db"])

def test_get_repo_packages_malformed(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("src.update_monitor.SCRIPT_DIR", ".")    
    with pytest.raises(tarfile.ReadError):
        get_repo_packages(["tests/files/malformed_core.db"])

@pytest.mark.parametrize(
    "version,expected",
    [
        [
         VersionFilters.Major,
         [("linux", "1.0.0", "2.0.0")]
        ],
        [
         VersionFilters.Minor,
         [("linux", "1.0.0", "2.0.0"), ("neovim", "0.7.0", "0.8.0")]
        ],
        [
         VersionFilters.Micro,
         [("linux", "1.0.0", "2.0.0"), ("neovim", "0.7.0", "0.8.0"), ("python3", "3.10.4", "3.10.5")]
        ],
        [
         VersionFilters.All,
         [("linux", "1.0.0", "2.0.0"), ("neovim", "0.7.0", "0.8.0"), ("python3", "3.10.4", "3.10.5")]
        ],
    ],
    ids=lambda x: x
)
def test_get_new_available(version, expected):
    current = {
        "linux": "1.0.0",
        "neovim": "0.7.0",
        "python3": "3.10.4"
    }
    newest = {
        "linux": "2.0.0",
        "neovim": "0.8.0",
        "python3": "3.10.5"
    }
    actual = get_new_available(current, newest, version)
    assert actual == expected

def test_get_new_available_none():
    current = {
        "linux": "1.0.0",
        "neovim": "0.7.0",
        "python3": "3.10.4"
    }
    actual = get_new_available(current, current, VersionFilters.All)
    assert actual == []

def test_get_new_available_versioning():
    current = {
            "some-weird-versioning": "2022-abcde",
    }
    newest = {
        "some-weird-versioning": "2022-abcdef",
    }
    expected = [("some-weird-versioning", "2022-abcde", "2022-abcdef")]
    actual = get_new_available(current, newest, VersionFilters.Major)
    assert actual == expected

def test_construct_html():
    actual = construct_html("title", [("linux", "1.0.0", "2.0.0")])
    with open("tests/files/expected_with_a_new_package.html") as f:
        expected = ''.join(f.readlines())
    assert actual == expected

def test_construct_html_no_new():
    actual = construct_html("title", [])
    expected = "<html><body><h3>title</h3></body></html>"
    assert actual == expected
