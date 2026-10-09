"""Provenance for actual local results, without personal paths or credentials."""

import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def environment_metadata() -> dict:
    def git(*args: str) -> str | None:
        try:
            return subprocess.run(
                ["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True,
                check=True, timeout=10,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None

    dependencies = {}
    for package in ("streamlit", "pytest"):
        try:
            dependencies[package] = version(package)
        except PackageNotFoundError:
            dependencies[package] = None
    status = git("status", "--porcelain")
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": git("rev-parse", "HEAD"),
        "worktree_dirty": None if status is None else bool(status),
        "python": platform.python_version(), "platform": platform.platform(),
        "dependencies": dependencies, "implementation": sys.implementation.name,
    }
