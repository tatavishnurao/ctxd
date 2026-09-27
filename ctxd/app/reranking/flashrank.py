from __future__ import annotations

import time
from pathlib import Path
from typing import Any, cast

import numpy as np
from flashrank import Ranker  # type: ignore[import-untyped]
from opentelemetry import trace

from ctxd.app.models.domain import ContextCandidate
from ctxd.app.observability.metrics import (
    RERANKER_CANDIDATES,
    RERANKER_INFERENCE_LATENCY_SECONDS,
    RERANKER_PREPARATION_LATENCY_SECONDS,
)
from ctxd.app.reranking.base import apply_scores

tracer = trace.get_tracer(__name__)


class FlashRankReranker:
    """Local ONNX cross-encoder using FlashRank's TinyBERT artifact."""

    model_id = "cross-encoder/ms-marco-TinyBERT-L-2-v2"
    source_revision = "81d1926f67cb8eee2c2be17ca9f793c7c3bd20cc"
    flashrank_model_name = "ms-marco-TinyBERT-L-2-v2"
    max_length = 512
    license = "Apache-2.0"

    def __init__(
        self,
        *,
        cache_dir: str | Path,
        offline: bool = False,
        batch_size: int = 16,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        cache = Path(cache_dir)
        if offline and not (cache / self.flashrank_model_name).is_dir():
            raise FileNotFoundError("reranker model is not present in the offline cache")
        self.batch_size = batch_size
        self._ranker = Ranker(
            model_name=self.flashrank_model_name,
            cache_dir=str(cache),
            max_length=self.max_length,
            log_level="WARNING",
        )
        self.last_timings_ms: dict[str, float] = {}

    def rerank(
        self, query: str, candidates: list[ContextCandidate], top_k: int
    ) -> list[ContextCandidate]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if not candidates:
            self.last_timings_ms = {
                "preparation": 0.0,
                "tokenization": 0.0,
                "inference": 0.0,
                "total": 0.0,
            }
            return []
        total_started = time.perf_counter()
        with tracer.start_as_current_span("reranker.prepare") as span:
            span.set_attribute("reranker.model", self.model_id)
            span.set_attribute("reranker.candidate_count", len(candidates))
            span.set_attribute("reranker.batch_size", self.batch_size)
            started = time.perf_counter()
            passages = [
                {"id": index, "text": candidate.content}
                for index, candidate in enumerate(candidates)
            ]
            preparation = time.perf_counter() - started
            RERANKER_PREPARATION_LATENCY_SECONDS.observe(preparation)
        scores: list[float] = []
        tokenization = 0.0
        inference = 0.0
        with tracer.start_as_current_span("reranker.inference") as span:
            span.set_attribute("reranker.model", self.model_id)
            span.set_attribute("reranker.candidate_count", len(candidates))
            span.set_attribute("reranker.batch_size", self.batch_size)
            tokenizer = cast(Any, self._ranker.tokenizer)
            session = cast(Any, self._ranker.session)
            for offset in range(0, len(passages), self.batch_size):
                batch = passages[offset : offset + self.batch_size]
                started = time.perf_counter()
                encoded = tokenizer.encode_batch([[query, row["text"]] for row in batch])
                tokenization += time.perf_counter() - started
                input_ids = np.asarray([item.ids for item in encoded], dtype=np.int64)
                attention_mask = np.asarray(
                    [item.attention_mask for item in encoded], dtype=np.int64
                )
                token_type_ids = np.asarray([item.type_ids for item in encoded], dtype=np.int64)
                inputs = {"input_ids": input_ids, "attention_mask": attention_mask}
                if not np.all(token_type_ids == 0):
                    inputs["token_type_ids"] = token_type_ids
                started = time.perf_counter()
                logits = session.run(None, inputs)[0]
                inference += time.perf_counter() - started
                if logits.shape[1] == 1:
                    batch_scores = 1.0 / (1.0 + np.exp(-logits.flatten()))
                else:
                    shifted = logits - np.max(logits, axis=1, keepdims=True)
                    probabilities = np.exp(shifted) / np.sum(np.exp(shifted), axis=1, keepdims=True)
                    batch_scores = probabilities[:, 1]
                scores.extend(float(score) for score in batch_scores)
            RERANKER_INFERENCE_LATENCY_SECONDS.observe(inference)
        RERANKER_CANDIDATES.observe(len(candidates))
        self.last_timings_ms = {
            "preparation": preparation * 1000,
            "tokenization": tokenization * 1000,
            "inference": inference * 1000,
            "total": (time.perf_counter() - total_started) * 1000,
        }
        return apply_scores(candidates, scores, top_k=top_k, model_id=self.model_id)
