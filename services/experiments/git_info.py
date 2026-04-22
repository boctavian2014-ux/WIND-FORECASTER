from __future__ import annotations

import subprocess
from pathlib import Path


def try_git_commit_sha(cwd: Path | None = None) -> str | None:
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None
