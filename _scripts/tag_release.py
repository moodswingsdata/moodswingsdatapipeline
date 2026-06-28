# This script figures out a tag name and creates it.

from datetime import date
from pathlib import Path
import subprocess

THIS_SCRIPT = __file__
THIS_REPO_DIR = (Path(THIS_SCRIPT) / '..' / '..').resolve()

from moodswings.models import SCHEMA_VERSION

# checks to make sure we've got the structures we expect
assert THIS_REPO_DIR.is_dir()
assert len(SCHEMA_VERSION) == 3

# figure out today
today = date.today()
today_for_tag = today.strftime('%Y-%m-%d')

schema_for_tag = f"{SCHEMA_VERSION[0]}.{SCHEMA_VERSION[1]}.{SCHEMA_VERSION[2]}"

TAG_NAME = f"v{schema_for_tag}/{today_for_tag}"

print(f"{THIS_REPO_DIR=}")
print(f"{SCHEMA_VERSION=}")
print(f"{TAG_NAME=}")

def run_git(work_dir, *args):
    """Run a Git subcommand, return its stdout if it's successful, raise if it exits non-zero"""
    proc = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=work_dir,
    )
    if proc.returncode != 0:
        raise SystemError(proc)
    return proc.stdout

our_branch = run_git(THIS_REPO_DIR, "symbolic-ref", "--short", "HEAD").strip()
if our_branch != 'main':
    print("WARNING: 🔧 This repo is not at main")
    print(f"It's at `{our_branch}`")
    input("Ctrl-C to cancel, otherwise press Enter to accept...")

dirty = False if run_git(THIS_REPO_DIR, "status", "--short").strip() == "" else True
if dirty:
    print("WARNING: 🔧 Repo has uncommitted changes")
    input("Ctrl-C to cancel, otherwise press Enter to accept...")

print()
input("Last chance to bail (Ctrl-C to stop, Enter to go)...")

print(run_git(THIS_REPO_DIR, "tag", "-a", TAG_NAME, "-m", TAG_NAME))
print("Now run `git push --tags`")
