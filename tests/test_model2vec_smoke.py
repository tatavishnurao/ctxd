"""Real pinned Model2Vec smoke test.

Gated because it needs the pinned model artifact (downloaded once, then cached).
Run with ``CTXD_RUN_MODEL2VEC=1``; set ``CTXD_EMBEDDING_OFFLINE=1`` to forbid
network access when the Hugging Face cache is pre-populated (CI caches it).
"""

import math
import os

import pytest
from ctxd.app.config.settings import Settings
from ctxd.app.models.domain import DocumentSourceType, RetrievalMode
from ctxd.app.retrieval.semantic import RealEmbeddingProvider
from ctxd.app.runtime import create_runtime
from ctxd.app.storage.documents import InMemoryDocumentStore

pytestmark = pytest.mark.skipif(
    os.getenv("CTXD_RUN_MODEL2VEC") != "1", reason="CTXD_RUN_MODEL2VEC=1 is not set"
)

OFFLINE = os.getenv("CTXD_EMBEDDING_OFFLINE", "").lower() in {"1", "true"}


@pytest.fixture(scope="module")
def provider() -> RealEmbeddingProvider:
    return RealEmbeddingProvider(offline=OFFLINE)


def test_pinned_model_is_normalized_deterministic_and_256_dimensional(
    provider: RealEmbeddingProvider,
) -> None:
    first = provider.embed_query("cache eviction under memory pressure")
    assert len(first) == 256
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0, rel_tol=1e-4)
    assert provider.embed_query("cache eviction under memory pressure") == first
    assert provider.version.startswith("model2vec:minishlab/potion-base-8M@bf8b0566")


def test_real_semantic_and_hybrid_rank_paraphrase_without_lexical_overlap() -> None:
    services = create_runtime(
        InMemoryDocumentStore(),
        Settings(embedding_provider="model2vec", embedding_offline=OFFLINE),
    )
    for path, content in {
        "cache.md": "The cache evicts least recently used entries when memory runs low.",
        "auth.md": "OAuth signing keys rotate every seven days.",
        "deploy.md": "A canary release routes a small share of traffic to the new version.",
    }.items():
        services.ingestion.ingest_content(
            content=content,
            source_path=path,
            source_type=DocumentSourceType.TEXT,
            tenant_id="t",
        )
    query = "How does the system make room when RAM is scarce?"
    for mode in (RetrievalMode.SEMANTIC, RetrievalMode.HYBRID):
        packet = services.assembler.assemble(
            query=query, tenant_id="t", top_k=3, max_context_tokens=1_000, retrieval_mode=mode
        )
        assert packet.candidates[0].metadata["source_path"] == "cache.md"
        assert packet.metadata["embedding_version"] == RealEmbeddingProvider.version
        assert "warnings" not in packet.metadata
