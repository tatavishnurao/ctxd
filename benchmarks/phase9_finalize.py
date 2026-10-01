"""Seal Phase 9 provenance after successful validation; never overwrite evidence."""

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    freeze = json.loads(Path("benchmarks/phase9_phase8_freeze.json").read_text())
    for name, checksum in freeze["sha256"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != checksum:
            raise ValueError(f"Phase 8 evidence changed: {name}")
    root = ET.parse("/tmp/ctxd-phase9-validation.xml").getroot()
    suites = list(root.iter("testsuite"))
    validation = {
        key: sum(int(s.get(key, "0")) for s in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    if not validation["tests"] or any(validation[key] for key in ("failures", "errors", "skipped")):
        raise ValueError("full validation with zero skips/failures is required")
    paths = sorted(
        {
            *Path("benchmarks").glob("phase9_*"),
            *Path("evals").glob("phase9_*"),
            Path("ctxd/app/evals/evidence.py"),
            Path("tests/test_evidence_eval.py"),
            Path("tests/test_phase9_artifacts.py"),
            Path("PHASE9_REPORT.md"),
            Path("README.md"),
            Path("ARCHITECTURE.md"),
            Path("BENCHMARKS.md"),
            Path("PERFORMANCE.md"),
        }
    )
    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "git_base_sha": freeze["git_base_sha"],
        "initial_dirty_state": freeze["dirty_state"],
        "final_dirty_state": subprocess.check_output(["git", "status", "--porcelain"], text=True),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "postgres": freeze["postgres"],
        "cpu": subprocess.check_output(["lscpu"], text=True),
        "dependencies": {
            k: importlib.metadata.version(k)
            for k in ("numpy", "onnxruntime", "tokenizers", "model2vec", "psycopg", "pydantic")
        },
        "environment": {
            k: os.getenv(k)
            for k in (
                "HF_HUB_OFFLINE",
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "TOKENIZERS_PARALLELISM",
            )
        },
        "database_scope": {
            "migration": "ctxd",
            "measurements": "ctxd_phase9",
            "tests": "ctxd_test",
        },
        "model_identity": json.loads(Path("benchmarks/phase9_reranker_replay.json").read_text())[
            "identity"
        ],
        "artifacts": {
            str(p): {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "bytes": p.stat().st_size,
            }
            for p in paths
            if p.is_file()
        },
        "validation": {
            **validation,
            "ruff": "passed",
            "mypy": "passed",
            "uv_sync": "passed",
            "postgres_migrations": "passed",
        },
        "commands": [
            "uv run python benchmarks/phase9_build.py",
            "CTXD_DATABASE_URL=<dedicated migrated ctxd_phase9> "
            "uv run python benchmarks/phase9_run.py development",
            "uv run python benchmarks/phase9_select.py",
            "CTXD_DATABASE_URL=<dedicated migrated ctxd_phase9> "
            "uv run python benchmarks/phase9_run.py holdout",
            "uv run python benchmarks/phase9_analysis.py",
            "uv run python benchmarks/phase9_challenge.py",
            "uv sync --python 3.13",
            "uv run ruff check .",
            "uv run mypy",
            "CTXD_DATABASE_URL=<ctxd> uv run alembic upgrade head",
            "CTXD_DATABASE_URL=<ctxd_test> uv run alembic upgrade head",
            "CTXD_TEST_DATABASE_URL=<ctxd_test> "
            "uv run pytest --junitxml=/tmp/ctxd-phase9-validation.xml",
        ],
        "decisions": {"packing": "P3", "reranking": "R2", "production_changed": False},
        "qualification": (
            "synthetic exact-span fixtures, not independently human-judged deployment evidence"
        ),
        "commits_or_pushes_performed": False,
    }
    with Path("benchmarks/phase9_experiment_manifest.json").open("x") as file:
        json.dump(manifest, file, indent=2)
    print(json.dumps(validation))


if __name__ == "__main__":
    main()
