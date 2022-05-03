from datetime import datetime
from argparse import ArgumentParser

import platform
import re
import os
import requests
import tarfile
import sys
import subprocess
import shutil

parser = ArgumentParser()
parser.add_argument("--nowarn", action="store_true", help="Disable package not found warning")

SCRIPT_PATH = os.path.dirname(sys.argv[0])

BAR_WIDTH = 50
def progress_bar(current: int | float, max_value: int | float):
    current_progress = current / max_value * BAR_WIDTH
    left_progress = BAR_WIDTH - int(current_progress)
    done_symbols = "=" * int(current_progress)
    left_symbols = "-" * left_progress
    print(f"\r[{done_symbols}{left_symbols}] {current_progress*100/BAR_WIDTH:.2f}%", end="")

def get_current_packages() -> dict:
    packages = {}
    process = subprocess.Popen([shutil.which("pacman"), "-Q"], stdout=subprocess.PIPE)
    lines = process.stdout.readlines()
    for line in lines:
        line = line.decode().strip().split(" ")
        name = line[0]
        version = line[1]
        packages[name] = version
    return packages

URL_REGEX = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&$\/\/=]*)"
def main() -> None:
    arch = platform.machine()
    try:
        with open("./repos.txt") as f:
            repos = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        repos = ["core", "extra", "community"]

    mirror: str = ""
    try:
        with open("/etc/pacman.d/mirrorlist") as f:
            for line in f:
                if res := re.search(URL_REGEX, line):
                    mirror = res[0]
                    break
    except FileNotFoundError:
        with open("./mirror.txt") as f:
            mirror = f.readline().strip()

    urls_to_query = []
    repo_files_to_download = []
    repo_files = []
    time_now = int(datetime.now().timestamp())
    for repo in repos:
        repo_file = f"{repo}.db"
        repo_files.append(repo_file)
        if os.path.isfile(repo_file):
            last_modified = int(os.path.getmtime(repo_file))
            time_since_modifed = time_now - last_modified
            # lets not download more than once an hour
            if time_since_modifed < 3600:
                print(f"{repo_file} is up to date")
                continue
        tmp: str = mirror.replace("$repo", repo).replace("$arch", arch)
        tmp += f"/{repo_file}"
        repo_files_to_download.append(repo_file)
        urls_to_query.append(tmp)

    for repo_file, url in zip(repo_files_to_download, urls_to_query):
        print(f"Downloading {repo_file}")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = r.headers.get("content-length", 0)
            downloaded_size = 0
            with open(os.path.join(SCRIPT_PATH, repo_file), "wb") as f:
                for data in r.iter_content(32 * 1024):
                    downloaded_size += len(data)
                    progress_bar(downloaded_size, int(total_size))
                    f.write(data)
                print()

    new_packages = {}
    for repo_file in repo_files:
        try:
            with tarfile.open(os.path.join(SCRIPT_PATH, repo_file), "r") as tar:
                for member in tar:
                    if member.isfile() and re.match(".*desc$", member.name):
                        name = ""
                        version = ""
                        with tar.extractfile(member) as f:
                            content = f.readlines()
                        for i, line in enumerate(content):
                            line = line.decode().strip()
                            if line == "%NAME%":
                                name = content[i+1].decode().strip()
                            elif line == "%VERSION%":
                                version = content[i+1].decode().strip()
                        if name == "" or version == "":
                            continue
                        new_packages[name] = version
        except FileNotFoundError:
            print(f"Could not find {repo_file}. Make sure it is in the script directory.")
        except tarfile.ReadError:
            print(f"Could not open malformed {repo_file}.")

    current_packages = get_current_packages()
    new_available = 0
    for package, version in current_packages.items():
        if package not in new_packages:
            if not args.nowarn:
                print(f"Warning {package} not found")
            continue
        if new_packages[package] != version:
            new_available += 1
            print(package, version, f"New version available ({new_packages[package]})")
    if new_available == 0:
        print("No new packages available")

if __name__ == "__main__":
    args = parser.parse_args()
    main()
