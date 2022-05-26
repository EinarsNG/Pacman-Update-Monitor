from pytest import MonkeyPatch
from email.message import EmailMessage

from src.update_monitor import (
    get_current_packages,
    get_new_available,
    get_repo_list,
    get_repo_packages,
    construct_html,
    get_mirror,
    get_urls,
    VersionFilters,
    NoUrlFound,
    send_notification,
)

import json
import tarfile
import pytest
import datetime

def test_get_packages(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("shutil.which", lambda _: "123")
    def create_process_mock(*_, **__):
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

def test_send_notification(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("src.update_monitor.SCRIPT_DIR", "tests/files")
    class DummySMTP:
        def __init__(self, *_, **kwargs):
            self.methodsCalled = 0
            assert kwargs["host"] == "example.com"
            assert kwargs["port"] == 587

        def starttls(self):
            self.methodsCalled += 1

        def login(self, username: str, password: str):
            self.methodsCalled += 1
            assert username == "abcd"
            assert password == "password"

        def send_message(self, msg: EmailMessage):
            self.methodsCalled += 1
            assert msg["Subject"] == "Update report"
            assert msg["From"] == "abcd@example.com"
            assert msg["To"] == "efgh@domain.com"
            assert msg.get_params()[0][0] == "text/html"
            assert msg.get_payload() == "<h3>Test</h3>"
            assert self.methodsCalled == 3

    monkeypatch.setattr("smtplib.SMTP.__init__", DummySMTP.__init__)
    monkeypatch.setattr("smtplib.SMTP.starttls", DummySMTP.starttls)
    monkeypatch.setattr("smtplib.SMTP.login", DummySMTP.login)
    monkeypatch.setattr("smtplib.SMTP.send_message", DummySMTP.send_message)
    send_notification("<h3>Test</h3>")

@pytest.mark.parametrize(
    "repofile,expected",
    [
        [
            "tests/files",
            ["a","b","c"]
        ],
        [
            "path/that/doesnt/exist",
            ["core", "extra", "community"]
        ]
    ],
    ids=lambda x: x
)
def test_get_repo_list(repofile, expected, monkeypatch: MonkeyPatch):
    monkeypatch.setattr("src.update_monitor.SCRIPT_DIR", repofile)
    actual = get_repo_list()
    assert actual == expected

def test_get_mirror_pass(monkeypatch: MonkeyPatch):
    class FileDummy:
        def __init__(self, path: str):
            assert path == "/etc/pacman.d/mirrorlist"

        def __iter__(self):
            self.lines = [
                    "#",
                    "#https://ignore.me.com/a/b/c",
                    "https://pick.me.com/c/d/e"
            ]
            return self

        def __next__(self):
            if not self.lines:
                raise StopIteration
            return self.lines.pop(0)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    monkeypatch.setattr("builtins.open", FileDummy)
    actual = get_mirror()
    expected = "https://pick.me.com/c/d/e"
    assert actual == expected

def test_get_mirror_fail(monkeypatch: MonkeyPatch):
    class FileDummy:
        def __enter__(self):
            return self
        
        def __exit__(self, *_):
            pass

        def readline(self):
            return "abcd"
    def raise_not_found(path):
        if path == "/etc/pacman.d/mirrorlist":
            raise FileNotFoundError()
        return FileDummy()
    monkeypatch.setattr("builtins.open", raise_not_found)
    with pytest.raises(NoUrlFound):
        get_mirror()

def test_get_urls():
    mirror = "https://example.com/$arch/$repo"
    repos = ["a", "b"]
    arch = "x86_64"
    expected = [
        "https://example.com/x86_64/a/a.db",
        "https://example.com/x86_64/b/b.db"
    ]
    actual = get_urls(mirror, repos, arch)
    assert actual == expected

def test_get_urls_fresh(monkeypatch: MonkeyPatch):
    class DatetimeDummy:
        @staticmethod
        def now():
            class NowDummy:
                def timestamp(self):
                    return 0
            return NowDummy()

    monkeypatch.setattr("os.path.isfile", lambda _: True)
    monkeypatch.setattr("os.path.getmtime", lambda _: 0)
    monkeypatch.setattr("src.update_monitor.datetime", DatetimeDummy)
    mirror = "abcd"
    repos = ["a"]
    arch = "aaa"
    actual = get_urls(mirror, repos, arch)
    assert actual == []

def test_download_repos():
    pass
