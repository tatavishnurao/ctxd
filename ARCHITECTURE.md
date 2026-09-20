# ctxd Architecture

## System shape

```text
Client
  -> API Gateway: tenant boundary, request IDs
  -> Document ingestion and deterministic context assembly
  -> Future: Model Router -> LLM -> Validator -> Tool Runtime -> Streaming
  -> Observability + Evaluation
```

## Phase 3 implemented path

```text
Document
  -> TextFileLoader / API content loader
  -> StructureAwareChunker
  -> DocumentStore (InMemoryDocumentStore | PostgresDocumentStore)
  -> Incremental tenant-scoped lexical index
  -> BM25Retriever
  -> ContextAssembler
  -> ContextPacket
```

### Ingestion

`ctxd/app/ingestion/loaders.py` accepts UTF-8 `.txt` and `.md` files and provides the validated content construction used by the API. It normalizes line endings, hashes normalized content with SHA-256, and creates a deterministic tenant-and-source-scoped document ID.

`ctxd/app/ingestion/chunking.py` identifies Markdown headings, paragraphs, fenced code blocks, and lists. Plain text uses paragraph boundaries. Oversized blocks prefer sentence boundaries and then use a hard approximate-token window. Chunk IDs include document identity, content hash, ordinal, and chunk content.

Token counting remains behind the `TokenCounter` protocol. The current word-and-punctuation counter is deterministic but is not a model tokenizer.

### Storage abstraction and runtime

`DocumentStore` remains the ingestion/storage boundary. Its `replace_document` operation atomically replaces a document and its complete chunk/index state. `LexicalIndex` is the retrieval/introspection boundary consumed by `BM25Retriever`. Both concrete backends implement both protocols so one consistency boundary owns document data and lexical state.

- `InMemoryDocumentStore` uses one `RLock` and incremental dictionaries/counters.
- `PostgresDocumentStore` uses a bounded psycopg pool and PostgreSQL transactions.
- `RuntimeServices` is application-scoped; no document/index correctness depends on Python module globals.
- Multiple runtimes connected to one database observe the same committed state.

The FastAPI lifespan opens and verifies the PostgreSQL pool at startup and closes it at shutdown. PostgreSQL startup requires Alembic revision `0001_phase3`; tables are never created from request handlers.

### PostgreSQL schema

The migration creates:

- `documents`: tenant/document key, source path/type, content/hash, JSON metadata, timestamps
- `chunks`: tenant/chunk key, document FK, ordinal, content/hash, token and lexical lengths, line range, metadata
- `lexical_corpus_stats`: tenant-local document count, chunk count, and total lexical length
- `lexical_terms`: tenant/term document frequency (`df`, measured over chunks)
- `lexical_postings`: tenant/term/chunk term frequency (`tf`)

Composite tenant keys and foreign keys prevent cross-tenant references. Chunk and posting rows cascade when a document is deleted.

### Why an explicit inverted index

PostgreSQL native full-text search was considered. It offers compact built-in indexes and simpler update SQL, but its dictionaries, stemming, normalization, and `ts_rank` semantics would change the Phase 2 tokenizer and BM25 ordering. Exact tenant-local `N`, `df`, `tf`, and average length would also be less explicit.

The implemented inverted index costs more rows and update complexity, but preserves the existing regex tokenizer and BM25 equation, makes tenant separation auditable, supports deterministic tie-breaking by `chunk_id`, and provides a clear future join point for hybrid retrieval without introducing semantic retrieval now.

### Transaction semantics

Changed-document ingestion executes in one transaction:

```text
BEGIN
  acquire document advisory lock
  lock tenant corpus-statistics row
  inspect/upsert document
  collect and remove old chunk/posting contributions
  insert new chunks and postings
  increment/decrement tenant term frequencies
  update tenant corpus statistics
COMMIT
```

Any error rolls back the document, chunks, postings, term frequencies, and corpus statistics together. Identical content returns without replacing rows. Concurrent updates of the same document serialize on an advisory lock. Updates for different documents in one tenant serialize only while changing shared tenant statistics.

Queries use normal PostgreSQL MVCC semantics: they observe either the complete state before replacement/deletion or the complete state after it, never an intermediate state.

### Incremental BM25

Index updates calculate tokens once during ingestion. Query-time work is limited to query tokenization, indexed posting lookup, and SQL scoring of matching chunks.

For each tenant the index maintains:

- `N`: chunk count
- `df(term)`: number of tenant chunks containing the term
- `tf(term, chunk)`: occurrence count in that chunk
- chunk lexical length
- total lexical length, from which average chunk length is calculated

The BM25 constants and equation remain `k1=1.5`, `b=0.75`, and:

```text
idf = ln(1 + (N - df + 0.5) / (df + 0.5))
```

Repeated query terms retain the Phase 2 query-frequency multiplier. Scores sort descending with `chunk_id` as the deterministic tie-breaker.

### Tenant isolation

The API treats `x-tenant-id` as authoritative and rejects mismatching request bodies. Every document/chunk/index key and every search join includes tenant ID. Corpus and term statistics are tenant-local, so another tenant cannot affect IDF.

### Context assembly

`ContextAssembler` preserves retrieval order and selects whole candidates that fit the token budget. Candidates that do not fit are dropped, not truncated. Packet metadata records retrieved/selected counts, token counts, budget drops, and `retrieval_type="lexical"`.

### Observability and failures

Bounded metrics cover database operation latency, index update latency, lexical search latency, ingestion, retrieval results, selected tokens, and budget drops. Span names include `database.document_upsert`, `database.chunk_replace`, `lexical.index_update`, `lexical.search`, and `context_assembly`. Raw documents, terms, queries, IDs, paths, and tenants are not metric labels or span attributes.

Database unavailability, malformed persisted metadata, failed transactions, and retrieval timeouts raise explicit errors. The API distinguishes timeouts (`504`) and unavailable retrieval (`503`) from a successful empty candidate list (`200`).

### Evaluation

The original 22-case corpus remains unchanged and produces the Phase 2 scores through both backends. The expanded corpus contains 30 documents and 100 cases covering exact terms, morphology variants, ambiguous/shared terms, near-duplicate content, multiple relevant documents, long chunks, rare terms, and tenant isolation.

## Deferred by design

Semantic/vector retrieval, reranking, dependency expansion, LLM inference, model routing, tools, SSE, frontend work, and distributed job infrastructure remain outside Phase 3.
