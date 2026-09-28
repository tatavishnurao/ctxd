"""Materialize a development-only baseline artifact to enforce selection isolation."""

from __future__ import annotations

import json
from pathlib import Path

source = Path("benchmarks/phase7_partition_baselines.json")
destination = Path("benchmarks/phase7_development_baseline.json")
if destination.exists():
    raise FileExistsError(f"refusing to overwrite {destination}")
artifact = json.loads(source.read_text(encoding="utf-8"))
destination.write_text(
    json.dumps(
        {
            "protocol": artifact["protocol"] | {"partition": "development only"},
            "metrics": artifact["partitions"]["development"],
            "category_metrics": artifact["by_category"]["development"],
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
