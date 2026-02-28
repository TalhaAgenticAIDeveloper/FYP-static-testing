"""
Scan Configuration
──────────────────
Defines which folders should be skipped during recursive
file extraction when a user uploads a project folder.

How to customise:
    • Edit the SKIP_FOLDERS list below, OR
    • Set the SKIP_FOLDERS env-var as a comma-separated string
      e.g.  SKIP_FOLDERS=venv,.venv,__pycache__,node_modules
    The env-var (if set) **overrides** the hardcoded list.
"""

import os
from pathlib import PurePosixPath, PureWindowsPath
from typing import Set

from dotenv import load_dotenv

load_dotenv()

# ── Default folders to skip ─────────────────────────────────────────────
# Add or remove entries as needed.  Matching is case-insensitive against
# every component of the file's relative path.
SKIP_FOLDERS: list[str] = [
    # Virtual environments
    "venv",
    ".venv",
    "env",
    ".env",
    "virtualenv",
    "conda-env",

    # Python internal / build artefacts
    "__pycache__",
    ".eggs",
    "egg-info",
    "dist",
    "build",
    "sdist",
    "site-packages",
    "lib",
    "Lib",
    "lib64",
    "Scripts",
    "Include",
    "share",

    # Package / dependency managers
    "node_modules",

    # Version control & editors
    ".git",
    ".svn",
    ".hg",
    ".idea",
    ".vscode",

    # Testing / linting caches
    ".tox",
    ".nox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    ".coverage",

    # Misc
    "migrations",
    ".terraform",
]

# ── Override from environment variable (optional) ────────────────────────
_env_override = os.getenv("SKIP_FOLDERS")
if _env_override:
    SKIP_FOLDERS = [f.strip() for f in _env_override.split(",") if f.strip()]


def _get_skip_set() -> Set[str]:
    """Return the skip-folder names as a lower-cased set for O(1) lookup."""
    return {name.lower() for name in SKIP_FOLDERS}


def should_skip_file(relative_path: str) -> bool:
    """
    Return True if *any* directory component of ``relative_path`` matches
    a folder name in SKIP_FOLDERS (case-insensitive).

    Works with both forward-slash and back-slash separators, and with
    browser-style paths (e.g. ``myproject/venv/lib/site.py``).

    Examples
    --------
    >>> should_skip_file("myproject/venv/lib/site.py")
    True
    >>> should_skip_file("myproject/src/app.py")
    False
    >>> should_skip_file("__pycache__/module.cpython-311.pyc")
    True
    """
    skip_set = _get_skip_set()

    # Normalise to forward slashes and split into parts
    normalised = relative_path.replace("\\", "/")
    parts = normalised.split("/")

    # Check every directory component (skip the last part – that's the filename)
    for part in parts[:-1]:
        if part.lower() in skip_set:
            return True
        # Also catch "something.egg-info" style names
        if any(part.lower().endswith(s) for s in skip_set if "-" in s or "." in s):
            return True

    return False
