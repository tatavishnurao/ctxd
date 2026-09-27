import hashlib
import json
from pathlib import Path


def test_phase5_artifacts_match_frozen_manifest() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (root / "benchmarks/phase5_artifact_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["git_base_sha"] == "aa900dd9eef79b0a39cae30dbd553605aa36c1ef"
    assert len(manifest["artifacts"]) == 10
    for expected in manifest["artifacts"]:
        artifact = root / expected["filename"]
        content = artifact.read_bytes()
        assert len(content) == expected["bytes"], expected["filename"]
        assert hashlib.sha256(content).hexdigest() == expected["sha256"], expected["filename"]
