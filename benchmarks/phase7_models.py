"""Pinned, local-only ONNX cross-encoder helpers for Phase 7 experiments."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from huggingface_hub import hf_hub_download
from onnxruntime import InferenceSession, SessionOptions
from tokenizers import Tokenizer


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    revision: str
    license: str
    onnx_file: str
    maximum_length: int = 512
    quantized: bool = False


MINILM_L6 = ModelSpec(
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "233902d25c440f23af6f7d6e94d2946bac0bee0a",
    "Apache-2.0",
    "onnx/model_quint8_avx2.onnx",
    quantized=True,
)
BGE_RERANKER_BASE = ModelSpec(
    "BAAI/bge-reranker-base",
    "2cfc18c9415c912f9d8155881c133215df768a70",
    "MIT",
    "onnx/model.onnx",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class LocalOnnxReranker:
    def __init__(
        self,
        spec: ModelSpec,
        *,
        cache_dir: Path,
        intra_op_threads: int = 4,
        offline: bool = False,
    ) -> None:
        if intra_op_threads <= 0:
            raise ValueError("intra_op_threads must be positive")
        local_files_only = offline or os.getenv("HF_HUB_OFFLINE") == "1"
        onnx_path = Path(
            hf_hub_download(
                spec.model_id,
                spec.onnx_file,
                revision=spec.revision,
                cache_dir=cache_dir,
                local_files_only=local_files_only,
            )
        )
        tokenizer_path = Path(
            hf_hub_download(
                spec.model_id,
                "tokenizer.json",
                revision=spec.revision,
                cache_dir=cache_dir,
                local_files_only=local_files_only,
            )
        )
        self.spec = spec
        self.onnx_path = onnx_path
        self.tokenizer_path = tokenizer_path
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length=spec.maximum_length, direction="right")
        self.tokenizer.enable_padding(direction="right")
        options = SessionOptions()
        options.intra_op_num_threads = intra_op_threads
        options.inter_op_num_threads = 1
        self.session = InferenceSession(
            str(onnx_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.intra_op_threads = intra_op_threads
        self.last_timings_ms: dict[str, float] = {}

    def score_pairs(self, query: str, passages: list[str], *, batch_size: int = 16) -> list[float]:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not passages:
            self.last_timings_ms = {"tokenization": 0.0, "inference": 0.0, "total": 0.0}
            return []
        total_started = perf_counter()
        tokenization = 0.0
        inference = 0.0
        scores: list[float] = []
        names = {item.name for item in self.session.get_inputs()}
        for offset in range(0, len(passages), batch_size):
            batch = passages[offset : offset + batch_size]
            start = perf_counter()
            encoded = self.tokenizer.encode_batch([[query, passage] for passage in batch])
            tokenization += perf_counter() - start
            input_map: dict[str, np.ndarray[Any, Any]] = {
                "input_ids": np.asarray([item.ids for item in encoded], dtype=np.int64),
                "attention_mask": np.asarray(
                    [item.attention_mask for item in encoded], dtype=np.int64
                ),
            }
            if "token_type_ids" in names:
                input_map["token_type_ids"] = np.asarray(
                    [item.type_ids for item in encoded], dtype=np.int64
                )
            start = perf_counter()
            output = np.asarray(self.session.run(None, input_map)[0])
            inference += perf_counter() - start
            values = output.reshape(len(batch), -1)
            if values.shape[1] == 1:
                # Preserve native scalar classification logits; monotonic transforms
                # do not affect ranking and can distort cross-model tie diagnostics.
                batch_scores = [float(logit) for logit in values[:, 0]]
            elif values.shape[1] >= 2:
                shifted = values - np.max(values, axis=1, keepdims=True)
                probabilities = np.exp(shifted) / np.sum(np.exp(shifted), axis=1, keepdims=True)
                batch_scores = [float(value) for value in probabilities[:, -1]]
            else:
                raise ValueError(f"unexpected ONNX output shape: {output.shape}")
            scores.extend(batch_scores)
        self.last_timings_ms = {
            "tokenization": tokenization * 1000,
            "inference": inference * 1000,
            "total": (perf_counter() - total_started) * 1000,
        }
        return scores

    def identity(self) -> dict[str, Any]:
        return {
            "model_id": self.spec.model_id,
            "revision": self.spec.revision,
            "license": self.spec.license,
            "onnx_artifact": {
                "filename": self.spec.onnx_file,
                "bytes": self.onnx_path.stat().st_size,
                "sha256": sha256_file(self.onnx_path),
            },
            "tokenizer_artifact": {
                "filename": "tokenizer.json",
                "bytes": self.tokenizer_path.stat().st_size,
                "sha256": sha256_file(self.tokenizer_path),
            },
            "maximum_input_length": self.spec.maximum_length,
            "backend": "ONNX Runtime CPUExecutionProvider",
            "dtype": "quantized uint8 ONNX"
            if self.spec.quantized
            else "model artifact default float32",
            "intra_op_threads": self.intra_op_threads,
            "execution_device": "CPU",
            "python_dependency_delta": [],
            "model_cache_total_bytes": sum(
                path.stat().st_size
                for path in self.onnx_path.parent.parent.rglob("*")
                if path.is_file()
            ),
        }


def rerank_order(scores: list[float]) -> list[int]:
    return sorted(range(len(scores)), key=lambda index: (-scores[index], index))
