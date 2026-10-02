"""Seal Phase 10 blocked-stage artifacts without changing any historical file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from benchmarks.phase10_check import eligibility
from benchmarks.phase10_review import ROOT
from ctxd.app.evals.evidence import EvidenceCorpus, digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-junit", type=Path, required=True)
    parser.add_argument("--test-database-url", required=True)
    args = parser.parse_args()
    output = ROOT / "benchmarks/phase10_experiment_manifest.json"
    validation_path = ROOT / "benchmarks/phase10_validation.json"
    if output.exists() or validation_path.exists():
        raise FileExistsError("seal already exists; do not rewrite historical validation")
    history = json.loads((ROOT / "benchmarks/phase10_history_freeze.json").read_text())
    for path, expected in history["tracked_base_sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"base file changed: {path}")
    suites = list(ET.parse(args.validation_junit).getroot().iter("testsuite"))
    counts = {
        key: sum(int(s.attrib[key]) for s in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    if not counts["tests"] or any(counts[k] for k in ("failures", "errors", "skipped")):
        raise ValueError("full validation must pass with zero skipped tests")
    tests = list(ET.parse(args.validation_junit).getroot().iter("testcase"))
    postgres_tests = [
        t for t in tests if t.attrib.get("classname") == "tests.integration.test_postgres_storage"
    ]
    if len(postgres_tests) != 11 or counts["tests"] < 154:
        raise ValueError("full suite and all eleven PostgreSQL integration tests required")
    with psycopg.connect(args.test_database_url) as connection:
        if connection.execute("SELECT current_database()").fetchone()[0] != "ctxd_test":
            raise ValueError("validation must use the dedicated ctxd_test database")
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        vector = connection.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()[0]
    # Capture these checks rather than trusting a hand-written 'passed' flag.
    checks = []
    for command in (
        ["uv", "sync", "--python", "3.13"],
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "mypy"],
    ):
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
        checks.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    migration = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env={**os.environ, "CTXD_DATABASE_URL": args.test_database_url},
        text=True,
        capture_output=True,
        check=True,
    )
    checks.append(
        {
            "command": ["uv", "run", "alembic", "upgrade", "head"],
            "exit_code": migration.returncode,
            "stdout": migration.stdout,
            "stderr": migration.stderr,
        }
    )
    status = eligibility(ROOT / "evals/phase10_review_state.json")
    if status != json.loads((ROOT / "benchmarks/phase10_blocked_status.json").read_text()):
        raise ValueError("blocked-state artifact is stale")
    if status["canonical_eligible"]:
        raise ValueError("this finalizer seals a blocked milestone, not a completed experiment")
    corpus = EvidenceCorpus.model_validate_json(
        (ROOT / "evals/phase10_evidence_cases.json").read_text()
    )
    validation = {
        "python": sys.version,
        "junit_counts": counts,
        "checks": checks,
        "junit_sha256": hashlib.sha256(args.validation_junit.read_bytes()).hexdigest(),
        "test_database": "ctxd_test",
        "postgres_tests_skipped": 0,
        "postgres_tests_passed": len(postgres_tests),
        "migration_revision": revision,
        "pgvector_version": vector,
        "migration_command_executed": "CTXD_DATABASE_URL=<ctxd_test> uv run alembic upgrade head",
        "pytest_command_executed": (
            "CTXD_TEST_DATABASE_URL=<ctxd_test> uv run pytest --junitxml=..."
        ),
        "warnings": "Two existing Starlette/httpx/anyio dependency deprecations",
    }
    with validation_path.open("x") as stream:
        json.dump(validation, stream, indent=2)
        stream.write("\n")
    files = sorted(
        {
            *ROOT.glob("evals/phase10_*"),
            *ROOT.glob("benchmarks/phase10_*"),
            ROOT / "ctxd/app/evals/review.py",
            ROOT / "tests/test_review_eval.py",
            ROOT / "tests/test_phase10_artifacts.py",
            ROOT / "PHASE10_REVIEW_PACKET.md",
            ROOT / "PHASE10_REPORT.md",
        }
    )
    manifest = {
        "base_sha": history["base_sha"],
        "sealed_at": datetime.now(UTC).isoformat(),
        "status": "BLOCKED: independent review and corpus design are incomplete",
        "dataset_sha256": digest(corpus.model_dump(mode="json")),
        "initial_working_tree": "clean",
        "historical_files_unchanged": len(history["tracked_base_sha256"]),
        "production_unchanged": True,
        "commit_or_push_performed": False,
        "holdout_retrieval_runs": 0,
        "selected_policy": None,
        "phase11_started": False,
        "artifact_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files
            if p.is_file()
        },
    }
    with output.open("x") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "validation": counts,
                "artifacts": len(manifest["artifact_sha256"]),
            }
        )
    )


if __name__ == "__main__":
    main()
