from pathlib import Path

import pytest
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.loaders import DocumentLoadError, TextFileLoader, document_from_content
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import DocumentSourceType
from ctxd.app.storage.documents import InMemoryDocumentStore


def make_service(config: ChunkingConfig | None = None) -> IngestionService:
    return IngestionService(InMemoryDocumentStore(), StructureAwareChunker(config))


def test_deterministic_ids_and_identical_reingestion() -> None:
    service = make_service(ChunkingConfig(target_tokens=8, max_tokens=12, overlap_tokens=0))
    first_document, first_chunks, first_created = service.ingest_content(
        content="First paragraph has useful words.\n\nSecond paragraph has other words.",
        source_path="notes/a.txt",
        source_type=DocumentSourceType.TEXT,
        tenant_id="tenant-a",
    )
    second_document, second_chunks, second_created = service.ingest_content(
        content="First paragraph has useful words.\r\n\r\nSecond paragraph has other words.",
        source_path="notes/a.txt",
        source_type=DocumentSourceType.TEXT,
        tenant_id="tenant-a",
    )
    assert first_created is True
    assert second_created is False
    assert first_document.document_id == second_document.document_id
    assert [chunk.chunk_id for chunk in first_chunks] == [chunk.chunk_id for chunk in second_chunks]
    assert len(service.store.list_chunks("tenant-a")) == len(first_chunks)


def test_changed_content_replaces_chunks_without_duplicates() -> None:
    service = make_service(ChunkingConfig(target_tokens=5, max_tokens=8, overlap_tokens=0))
    document, old_chunks, _ = service.ingest_content(
        content="alpha beta gamma delta epsilon zeta",
        source_path="a.txt",
        source_type=DocumentSourceType.TEXT,
        tenant_id="tenant-a",
    )
    _, new_chunks, created = service.ingest_content(
        content="new content only",
        source_path="a.txt",
        source_type=DocumentSourceType.TEXT,
        tenant_id="tenant-a",
    )
    assert created is False
    assert {chunk.chunk_id for chunk in old_chunks}.isdisjoint(
        {chunk.chunk_id for chunk in new_chunks}
    )
    assert service.store.list_chunks("tenant-a", document.document_id) == new_chunks


def test_markdown_chunking_preserves_structure_and_metadata() -> None:
    service = make_service(ChunkingConfig(target_tokens=12, max_tokens=20, overlap_tokens=0))
    document, chunks, _ = service.ingest_content(
        content=(
            "# Setup\n\nInstall the service before starting it.\n\n"
            "- configure storage\n- configure logging\n\n"
            "```python\nprint('ready')\n```\n"
        ),
        source_path="guide.md",
        source_type=DocumentSourceType.MARKDOWN,
        tenant_id="tenant-a",
        metadata={"team": "platform"},
    )
    assert chunks
    assert all(chunk.content.strip() for chunk in chunks)
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert any("code" in chunk.metadata["block_types"] for chunk in chunks)
    assert all(chunk.metadata["team"] == "platform" for chunk in chunks)
    assert all(chunk.document_id == document.document_id for chunk in chunks)


def test_plain_text_uses_paragraph_and_sentence_fallback() -> None:
    service = make_service(ChunkingConfig(target_tokens=6, max_tokens=8, overlap_tokens=0))
    _, chunks, _ = service.ingest_content(
        content="One short sentence. A second sentence is longer. A final sentence ends.\n\nNext.",
        source_path="notes.txt",
        source_type=DocumentSourceType.TEXT,
        tenant_id="tenant-a",
    )
    assert len(chunks) >= 2
    assert all(chunk.token_count <= 8 for chunk in chunks)
    assert chunks[0].start_line == 1


def test_chunk_hard_max_for_oversized_code_block() -> None:
    service = make_service(ChunkingConfig(target_tokens=10, max_tokens=12, overlap_tokens=2))
    code = " ".join(f"value_{index}" for index in range(80))
    _, chunks, _ = service.ingest_content(
        content=f"```python\n{code}\n```",
        source_path="large.md",
        source_type=DocumentSourceType.MARKDOWN,
        tenant_id="tenant-a",
    )
    assert len(chunks) > 1
    assert max(chunk.token_count for chunk in chunks) <= 12


def test_file_loader_supports_txt_md_and_normalizes_lines(tmp_path: Path) -> None:
    path = tmp_path / "readme.md"
    path.write_bytes(b"# Heading\r\n\r\nBody\r\n")
    document = TextFileLoader().load(path, "tenant-a")
    assert document.source_type == DocumentSourceType.MARKDOWN
    assert "\r" not in document.content
    assert document.metadata["encoding"] == "utf-8"


def test_file_loader_rejects_unsupported_and_invalid_utf8(tmp_path: Path) -> None:
    unsupported = tmp_path / "data.pdf"
    unsupported.write_text("data", encoding="utf-8")
    with pytest.raises(DocumentLoadError, match="unsupported"):
        TextFileLoader().load(unsupported, "tenant-a")
    invalid = tmp_path / "bad.txt"
    invalid.write_bytes(b"\xff")
    with pytest.raises(DocumentLoadError, match="UTF-8"):
        TextFileLoader().load(invalid, "tenant-a")


def test_document_identity_is_tenant_scoped() -> None:
    first = document_from_content(
        content="same",
        source_path="same.txt",
        source_type=DocumentSourceType.TEXT,
        tenant_id="tenant-a",
    )
    second = document_from_content(
        content="same",
        source_path="same.txt",
        source_type=DocumentSourceType.TEXT,
        tenant_id="tenant-b",
    )
    assert first.document_id != second.document_id
