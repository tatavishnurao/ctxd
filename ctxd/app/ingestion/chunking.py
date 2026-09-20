import hashlib
import re
from dataclasses import dataclass
from typing import Protocol

from ctxd.app.models.domain import Chunk, Document, DocumentSourceType

_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])(?:\s+|$)")


class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...

    def spans(self, text: str) -> list[tuple[int, int]]: ...


class ApproximateTokenCounter:
    """Deterministic word-and-punctuation token approximation."""

    def count(self, text: str) -> int:
        return len(_TOKEN_RE.findall(text))

    def spans(self, text: str) -> list[tuple[int, int]]:
        return [(match.start(), match.end()) for match in _TOKEN_RE.finditer(text)]


@dataclass(frozen=True)
class ChunkingConfig:
    target_tokens: int = 400
    max_tokens: int = 600
    overlap_tokens: int = 40

    def __post_init__(self) -> None:
        if self.target_tokens <= 0:
            raise ValueError("target_tokens must be positive")
        if self.max_tokens < self.target_tokens:
            raise ValueError("max_tokens must be greater than or equal to target_tokens")
        if self.overlap_tokens < 0 or self.overlap_tokens >= self.target_tokens:
            raise ValueError("overlap_tokens must be non-negative and less than target_tokens")


@dataclass(frozen=True)
class _Block:
    content: str
    start_line: int
    end_line: int
    kind: str


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _make_block(source: str, start: int, end: int, kind: str) -> _Block | None:
    while start < end and source[start].isspace():
        start += 1
    while end > start and source[end - 1].isspace():
        end -= 1
    if start >= end:
        return None
    return _Block(
        content=source[start:end],
        start_line=_line_number(source, start),
        end_line=_line_number(source, max(start, end - 1)),
        kind=kind,
    )


def _plain_blocks(source: str) -> list[_Block]:
    blocks: list[_Block] = []
    start = 0
    for separator in re.finditer(r"\n[ \t]*\n", source):
        block = _make_block(source, start, separator.start(), "paragraph")
        if block:
            blocks.append(block)
        start = separator.end()
    final_block = _make_block(source, start, len(source), "paragraph")
    if final_block:
        blocks.append(final_block)
    return blocks


def _markdown_blocks(source: str) -> list[_Block]:
    lines = source.splitlines(keepends=True)
    offsets: list[int] = []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line)

    blocks: list[_Block] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        start_index = index
        stripped = line.lstrip()
        kind = "paragraph"
        if stripped.startswith("```") or stripped.startswith("~~~"):
            kind = "code"
            fence = stripped[:3]
            index += 1
            while index < len(lines):
                closing = lines[index].lstrip().startswith(fence)
                index += 1
                if closing:
                    break
        elif re.match(r"^#{1,6}\s+", stripped):
            kind = "heading"
            index += 1
        elif re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)", stripped):
            kind = "list"
            index += 1
            while index < len(lines):
                candidate = lines[index]
                if not candidate.strip():
                    break
                if not re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", candidate):
                    break
                index += 1
        else:
            index += 1
            while index < len(lines) and lines[index].strip():
                candidate = lines[index].lstrip()
                if candidate.startswith(("```", "~~~")) or re.match(
                    r"^(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+)", candidate
                ):
                    break
                index += 1
        start = offsets[start_index]
        end = offsets[index] if index < len(offsets) else len(source)
        block = _make_block(source, start, end, kind)
        if block:
            blocks.append(block)
    return blocks


def _split_oversized(
    block: _Block,
    max_tokens: int,
    counter: TokenCounter,
) -> list[_Block]:
    if counter.count(block.content) <= max_tokens:
        return [block]

    # Prefer sentence boundaries before the hard token window.
    boundaries = [match.end() for match in _SENTENCE_END_RE.finditer(block.content)]
    spans = counter.spans(block.content)
    result: list[_Block] = []
    token_start = 0
    while token_start < len(spans):
        token_end = min(token_start + max_tokens, len(spans))
        char_start = spans[token_start][0]
        char_limit = spans[token_end - 1][1]
        preferred = max(
            (boundary for boundary in boundaries if char_start < boundary <= char_limit),
            default=char_limit,
        )
        actual_end = preferred
        included = token_start
        while included < len(spans) and spans[included][1] <= actual_end:
            included += 1
        if included == token_start:
            included = token_end
            actual_end = spans[included - 1][1]
        part = block.content[char_start:actual_end].strip()
        if part:
            prefix = block.content[:char_start]
            result.append(
                _Block(
                    content=part,
                    start_line=block.start_line + prefix.count("\n"),
                    end_line=block.start_line + block.content[:actual_end].count("\n"),
                    kind=block.kind,
                )
            )
        token_start = included
    return result


def deterministic_chunk_id(document: Document, ordinal: int, content: str) -> str:
    digest = hashlib.sha256(
        f"{document.document_id}\0{document.content_hash}\0{ordinal}\0{content}".encode()
    ).hexdigest()
    return f"chk_{digest[:24]}"


class StructureAwareChunker:
    def __init__(
        self,
        config: ChunkingConfig | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        self.config = config or ChunkingConfig()
        self.token_counter = token_counter or ApproximateTokenCounter()

    def chunk(self, document: Document) -> list[Chunk]:
        blocks = (
            _markdown_blocks(document.content)
            if document.source_type == DocumentSourceType.MARKDOWN
            else _plain_blocks(document.content)
        )
        split_blocks = [
            part
            for block in blocks
            for part in _split_oversized(block, self.config.max_tokens, self.token_counter)
        ]
        groups: list[list[_Block]] = []
        index = 0
        while index < len(split_blocks):
            group: list[_Block] = []
            group_tokens = 0
            cursor = index
            while cursor < len(split_blocks):
                block = split_blocks[cursor]
                block_tokens = self.token_counter.count(block.content)
                separator_tokens = 1 if group else 0
                exceeds_target = (
                    group_tokens + separator_tokens + block_tokens > self.config.target_tokens
                )
                if group and exceeds_target:
                    break
                if group_tokens + separator_tokens + block_tokens > self.config.max_tokens:
                    break
                group.append(block)
                group_tokens += separator_tokens + block_tokens
                cursor += 1
            if not group:
                group = [split_blocks[index]]
                cursor = index + 1
            groups.append(group)

            next_index = cursor
            if cursor < len(split_blocks):
                overlap = 0
                for retained_index in range(len(group) - 1, 0, -1):
                    retained_tokens = self.token_counter.count(group[retained_index].content)
                    if overlap + retained_tokens > self.config.overlap_tokens:
                        break
                    overlap += retained_tokens
                    next_index = index + retained_index
            # Always advance; a single large block must not overlap with itself.
            index = max(index + 1, next_index)

        chunks: list[Chunk] = []
        for ordinal, group in enumerate(groups):
            content = "\n\n".join(block.content for block in group).strip()
            if not content:
                continue
            token_count = self.token_counter.count(content)
            if token_count > self.config.max_tokens:
                raise RuntimeError("chunker produced a chunk above the configured hard maximum")
            metadata: dict[str, str | int | float | bool | None | list[str]] = {
                "source_path": document.source_path,
                "content_hash": document.content_hash,
                "block_types": [block.kind for block in group],
            }
            for key, value in document.metadata.items():
                metadata.setdefault(key, value)
            chunks.append(
                Chunk(
                    chunk_id=deterministic_chunk_id(document, ordinal, content),
                    document_id=document.document_id,
                    tenant_id=document.tenant_id,
                    content=content,
                    content_hash=hashlib.sha256(content.encode()).hexdigest(),
                    start_line=group[0].start_line,
                    end_line=group[-1].end_line,
                    token_count=token_count,
                    ordinal=ordinal,
                    metadata=metadata,
                )
            )
        return chunks
