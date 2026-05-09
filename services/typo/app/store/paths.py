"""Path helpers for Lume backend.

repo_root() walks up from this file's location until it finds pnpm-workspace.yaml.
Falls back to LUME_REPO_ROOT env var if set.

db_path() returns the configured SQLite path (LUME_DB_PATH env override or default).
"""
import os
from pathlib import Path


def repo_root() -> Path:
    """Walk up from this file until pnpm-workspace.yaml is found."""
    env_root = os.environ.get("LUME_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()

    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pnpm-workspace.yaml").exists():
            return parent

    # Fallback: 4 levels up from this file (services/typo/app/store/paths.py)
    return current.parents[3]


def db_path() -> Path:
    """Return the SQLite database path."""
    env_path = os.environ.get("LUME_DB_PATH")
    if env_path:
        return Path(env_path).resolve()
    return repo_root() / "services" / "typo" / "seed.db"
