"""Capture historical file hashes and environment before Phase 10 corpus construction."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def main() -> None:
    base = command("git", "rev-parse", "60ccda0")
    paths = command("git", "ls-tree", "-r", "--name-only", base).splitlines()
    hashes = {}
    for path in paths:
        original = subprocess.check_output(["git", "show", f"{base}:{path}"], cwd=ROOT)
        if (ROOT / path).read_bytes() != original:
            raise RuntimeError(f"historical file changed: {path}")
        hashes[path] = hashlib.sha256(original).hexdigest()
    artifact = {
        "base_sha": base,
        "captured_at": datetime.now(UTC).isoformat(),
        "initial_tree_observation": "clean: git status --short and git diff --stat were empty",
        "initial_observation_timing": "session start, before Phase 10 changes",
        "capture_timing": "after initial offline review module draft; before corpus/retrieval work",
        "status_at_capture": command("git", "status", "--short"),
        "tracked_base_sha256": hashes,
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "uv": command("uv", "--version"),
        "installed_dependencies": command("uv", "pip", "freeze").splitlines(),
        "thread_environment": {
            k: os.environ.get(k)
            for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")
        },
        "production_changes_permitted": False,
        "push_permitted": False,
    }
    with (ROOT / "benchmarks/phase10_history_freeze.json").open("x") as output:
        json.dump(artifact, output, indent=2, sort_keys=True)
        output.write("\n")


if __name__ == "__main__":
    main()
