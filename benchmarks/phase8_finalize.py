"""Seal Phase 8 artifacts without overwriting previous evidence."""

import hashlib
import json
import subprocess
from pathlib import Path


def main() -> None:
    initial = json.loads(Path("benchmarks/phase8_initial_manifest.json").read_text())
    for name, digest in initial["historical_artifacts"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"historical evidence changed: {name}")
    paths = sorted(
        set(Path("benchmarks").glob("phase8_*"))
        | {
            Path("ctxd/app/evals/context_selection.py"),
            Path("ctxd/app/evals/retrieval.py"),
            Path("tests/test_context_selection.py"),
            Path("tests/test_phase8_artifacts.py"),
            Path("PHASE8_REPORT.md"),
            Path("README.md"),
            Path("ARCHITECTURE.md"),
            Path("BENCHMARKS.md"),
            Path("PERFORMANCE.md"),
        }
    )
    manifest = {
        "initial_state": initial,
        "final_git_status": subprocess.check_output(["git", "status", "--porcelain"], text=True),
        "artifacts": {
            str(p): {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "bytes": p.stat().st_size,
            }
            for p in paths
            if p.is_file()
        },
        "commands": [
            "uv run python benchmarks/phase8_profile.py",
            "uv run python benchmarks/phase8_audit.py (before duplicate-gain repair)",
            "uv run python benchmarks/phase8_freeze.py",
            "uv run python benchmarks/phase8_holdout.py",
            "uv sync --python 3.13",
            "uv run ruff check .",
            "uv run mypy",
            "CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd "
            "uv run alembic upgrade head",
            "CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_test "
            "uv run alembic upgrade head",
            "CTXD_TEST_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_test uv run pytest",
        ],
        "validation": {
            "passed": 104,
            "skipped": 0,
            "ruff": "pass",
            "mypy": "pass",
            "postgres": "migrations and all integration tests pass",
        },
        "production_changed": False,
        "decisions": {"reranking": "R2", "packing": "C1"},
        "not_completed": [
            "full database-path profiling",
            "packing holdout (no selected candidate)",
            "combined path (quality gates failed)",
            "survivor scale/load benchmarks",
        ],
        "git_commit_or_push_performed": False,
    }
    with Path("benchmarks/phase8_experiment_manifest.json").open("x") as file:
        json.dump(manifest, file, indent=2)


if __name__ == "__main__":
    main()
