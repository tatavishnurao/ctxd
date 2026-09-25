"""Versioned tenant-scoped pgvector embeddings (exact cosine search)."""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_phase4"
down_revision: str | None = "0001_phase3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # An unconstrained vector column permits the 128-dimensional deterministic
    # fixture and 256-dimensional real baseline to coexist by version. Queries
    # always filter version and dimension before applying cosine distance.
    op.execute(
        """
        CREATE TABLE chunk_embeddings (
            tenant_id text NOT NULL,
            chunk_id text NOT NULL,
            embedding_version text NOT NULL,
            embedding vector NOT NULL,
            dimension integer NOT NULL CHECK (dimension > 0),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (tenant_id, chunk_id),
            FOREIGN KEY (tenant_id, chunk_id)
                REFERENCES chunks (tenant_id, chunk_id) ON DELETE CASCADE
        );
        CREATE INDEX chunk_embeddings_tenant_version_idx
            ON chunk_embeddings (tenant_id, embedding_version);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE chunk_embeddings")
