"""Phase 3 persistent documents and lexical index.

Revision ID: 0001_phase3
Revises:
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_phase3"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE documents (
            tenant_id text NOT NULL,
            document_id text NOT NULL,
            source_path text NOT NULL,
            source_type text NOT NULL CHECK (source_type IN ('text', 'markdown')),
            content text NOT NULL,
            content_hash text NOT NULL,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (tenant_id, document_id),
            UNIQUE (tenant_id, source_path)
        );

        CREATE TABLE chunks (
            tenant_id text NOT NULL,
            chunk_id text NOT NULL,
            document_id text NOT NULL,
            ordinal integer NOT NULL CHECK (ordinal >= 0),
            content text NOT NULL CHECK (length(content) > 0),
            content_hash text NOT NULL,
            token_count integer NOT NULL CHECK (token_count > 0),
            lexical_length integer NOT NULL CHECK (lexical_length >= 0),
            start_line integer NOT NULL CHECK (start_line > 0),
            end_line integer NOT NULL CHECK (end_line >= start_line),
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (tenant_id, chunk_id),
            UNIQUE (tenant_id, document_id, ordinal),
            FOREIGN KEY (tenant_id, document_id)
                REFERENCES documents (tenant_id, document_id) ON DELETE CASCADE
        );

        CREATE INDEX chunks_tenant_document_idx
            ON chunks (tenant_id, document_id, ordinal);

        CREATE TABLE lexical_corpus_stats (
            tenant_id text PRIMARY KEY,
            indexed_documents bigint NOT NULL DEFAULT 0 CHECK (indexed_documents >= 0),
            chunk_count bigint NOT NULL DEFAULT 0 CHECK (chunk_count >= 0),
            total_chunk_length bigint NOT NULL DEFAULT 0 CHECK (total_chunk_length >= 0),
            updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE lexical_terms (
            tenant_id text NOT NULL,
            term text NOT NULL,
            document_frequency bigint NOT NULL CHECK (document_frequency >= 0),
            PRIMARY KEY (tenant_id, term)
        );

        CREATE TABLE lexical_postings (
            tenant_id text NOT NULL,
            term text NOT NULL,
            chunk_id text NOT NULL,
            term_frequency integer NOT NULL CHECK (term_frequency > 0),
            PRIMARY KEY (tenant_id, term, chunk_id),
            FOREIGN KEY (tenant_id, term)
                REFERENCES lexical_terms (tenant_id, term) ON DELETE CASCADE,
            FOREIGN KEY (tenant_id, chunk_id)
                REFERENCES chunks (tenant_id, chunk_id) ON DELETE CASCADE
        );

        CREATE INDEX lexical_postings_chunk_idx
            ON lexical_postings (tenant_id, chunk_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE lexical_postings;
        DROP TABLE lexical_terms;
        DROP TABLE lexical_corpus_stats;
        DROP TABLE chunks;
        DROP TABLE documents;
        """
    )
