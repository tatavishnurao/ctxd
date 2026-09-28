"""Development-only cached-pool ONNX decomposition; not a database/HTTP benchmark."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from phase7_models import MINILM_L6, LocalOnnxReranker


def score(model: LocalOnnxReranker, query: str, passages: list[str], batch: int) -> dict[str, Any]:
    total_start = perf_counter()
    timings = dict.fromkeys(
        ("pairs", "tokenization", "tensors", "inference", "conversion", "sort"), 0.0
    )
    start = perf_counter()
    pairs = [[query, passage] for passage in passages]
    timings["pairs"] = perf_counter() - start
    names = {i.name for i in model.session.get_inputs()}
    scores: list[float] = []
    actual_tokens = padded_tokens = 0
    for offset in range(0, len(pairs), batch):
        start = perf_counter()
        encoded = model.tokenizer.encode_batch(pairs[offset : offset + batch])
        timings["tokenization"] += perf_counter() - start
        start = perf_counter()
        inputs = {
            "input_ids": np.asarray([e.ids for e in encoded], dtype=np.int64),
            "attention_mask": np.asarray([e.attention_mask for e in encoded], dtype=np.int64),
        }
        if "token_type_ids" in names:
            inputs["token_type_ids"] = np.asarray([e.type_ids for e in encoded], dtype=np.int64)
        timings["tensors"] += perf_counter() - start
        start = perf_counter()
        output = model.session.run(None, inputs)[0]
        timings["inference"] += perf_counter() - start
        start = perf_counter()
        values = np.asarray(output).reshape(len(encoded), -1)
        if values.shape[1] != 1:
            raise ValueError("profile expects pinned MiniLM scalar logits")
        scores.extend(float(v) for v in values[:, 0])
        timings["conversion"] += perf_counter() - start
        actual_tokens += sum(sum(e.attention_mask) for e in encoded)
        padded_tokens += sum(len(e.ids) for e in encoded)
    start = perf_counter()
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    timings["sort"] = perf_counter() - start
    timings["total"] = perf_counter() - total_start
    return {
        "ms": {k: v * 1000 for k, v in timings.items()},
        "scores": scores,
        "order": order,
        "actual_tokens": actual_tokens,
        "padded_tokens": padded_tokens,
    }


def main() -> None:
    output = Path("benchmarks/phase8_profile.json")
    if output.exists():
        raise FileExistsError(output)
    pools = json.loads(Path("benchmarks/phase7_candidate_pools.json").read_text())["cases"]
    dev = sorted(
        (r for r in pools if r["partition"] == "development"),
        key=lambda r: sum(c["token_cost"] for c in r["candidate_sources"]),
    )
    cases = [dev[0], dev[len(dev) // 2], dev[-1]]
    rows = []
    initialization = []
    reference: dict[tuple[str, int], list[int]] = {}
    for threads in (4, 1, 2):
        start = perf_counter()
        model = LocalOnnxReranker(
            MINILM_L6,
            cache_dir=Path.home() / ".cache/ctxd/phase7",
            intra_op_threads=threads,
            offline=True,
        )
        initialization.append(
            {"threads": threads, "cached_model_construction_ms": (perf_counter() - start) * 1000}
        )
        for n in (5, 10, 20):
            for case in cases:
                passages = [r["content"] for r in case["candidate_sources"][:n]]
                for batch in (16, 8, 1):
                    for repeat in range(3):
                        result = score(model, case["query"], passages, batch)
                        key = (case["case_id"], n)
                        reference.setdefault(key, result["order"])
                        rows.append(
                            {
                                "case_id": case["case_id"],
                                "threads": threads,
                                "n": n,
                                "batch": batch,
                                "repeat": repeat,
                                "same_order_as_first_threads4_batch16": result["order"]
                                == reference[key],
                                **result,
                            }
                        )
        del model
    with output.open("x") as file:
        json.dump(
            {
                "scope": "three length-stratified development pools; 3 repeats per cell",
                "cold_scope": "cached construction and first call, not OS-cold download",
                "not_measured": [
                    "database retrieval",
                    "materialization",
                    "executor overhead",
                    "metadata copying",
                    "HTTP",
                    "PostgreSQL CPU",
                ],
                "initialization": initialization,
                "raw": rows,
            },
            file,
            indent=2,
        )
    print(f"wrote {output}: {len(rows)} scorer calls")


if __name__ == "__main__":
    main()
