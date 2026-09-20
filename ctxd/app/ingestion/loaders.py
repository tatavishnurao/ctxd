import hashlib
from pathlib import Path
from typing import Protocol

from ctxd.app.models.domain import Document, DocumentSourceType

Metadata = dict[str, str | int | float | bool | None]


class DocumentLoadError(ValueError):
    """Raised when a source cannot be loaded as a supported document."""


class DocumentLoader(Protocol):
    def load(
        self,
        source_path: Path,
        tenant_id: str,
        metadata: Metadata | None = None,
    ) -> Document: ...


def normalize_content(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def deterministic_document_id(tenant_id: str, source_path: str) -> str:
    identity = f"{tenant_id}\0{source_path}"
    return f"doc_{hashlib.sha256(identity.encode()).hexdigest()[:24]}"


def document_from_content(
    *,
    content: str,
    source_path: str,
    source_type: DocumentSourceType,
    tenant_id: str,
    metadata: Metadata | None = None,
) -> Document:
    normalized = normalize_content(content)
    if not normalized.strip():
        raise DocumentLoadError("document content is empty")
    normalized_path = Path(source_path).as_posix()
    combined_metadata: Metadata = {
        "extension": Path(normalized_path).suffix.lower(),
        "encoding": "utf-8",
    }
    if metadata:
        combined_metadata.update(metadata)
    return Document(
        document_id=deterministic_document_id(tenant_id, normalized_path),
        tenant_id=tenant_id,
        source_path=normalized_path,
        source_type=source_type,
        content=normalized,
        content_hash=content_sha256(normalized),
        metadata=combined_metadata,
    )


class TextFileLoader:
    _types = {
        ".txt": DocumentSourceType.TEXT,
        ".md": DocumentSourceType.MARKDOWN,
    }

    def load(
        self,
        source_path: Path,
        tenant_id: str,
        metadata: Metadata | None = None,
    ) -> Document:
        suffix = source_path.suffix.lower()
        source_type = self._types.get(suffix)
        if source_type is None:
            raise DocumentLoadError(f"unsupported document type: {suffix or '<none>'}")
        try:
            content = source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentLoadError(f"document is not valid UTF-8: {source_path}") from exc
        except OSError as exc:
            raise DocumentLoadError(f"could not read document {source_path}: {exc}") from exc
        file_metadata: Metadata = {
            "filename": source_path.name,
            "size_bytes": source_path.stat().st_size,
        }
        if metadata:
            file_metadata.update(metadata)
        return document_from_content(
            content=content,
            source_path=str(source_path),
            source_type=source_type,
            tenant_id=tenant_id,
            metadata=file_metadata,
        )
