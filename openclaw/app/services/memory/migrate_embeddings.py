"""One-time migration: re-embed all vector memories from 384-dim to 1024-dim (bge-m3).

Idempotent — checks current column dimension before running.
"""

import logging

import sqlalchemy
from sqlalchemy import text

from app.services.db import engine, get_session
from app.services.memory.vector_store import EMBEDDING_DIM, embed
from app.services.models import VectorMemory

logger = logging.getLogger(__name__)


def _get_vector_dim() -> int | None:
    """Return the current vector dimension of vector_memories.embedding, or None if table missing."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = 'vector_memories'::regclass "
                "AND attname = 'embedding'"
            )
        ).fetchone()
        if row is None:
            return None
        return row[0]


def migrate_embedding_dimension() -> None:
    """Alter vector column to 1024-dim and re-embed all rows. Skips if already migrated."""
    try:
        current_dim = _get_vector_dim()
    except Exception:
        logger.info("vector_memories table does not exist yet; skipping embedding migration")
        return

    if current_dim == EMBEDDING_DIM:
        logger.info("Embedding dimension already %d; skipping migration", EMBEDDING_DIM)
        return

    logger.info("Migrating embeddings from %d-dim to %d-dim...", current_dim or 0, EMBEDDING_DIM)

    # Step 1: alter column type
    with engine.connect() as conn:
        conn.execute(
            text(f"ALTER TABLE vector_memories ALTER COLUMN embedding TYPE vector({EMBEDDING_DIM})")
        )
        conn.commit()

    # Step 2: re-embed all rows in batches
    with get_session() as s:
        rows = s.query(VectorMemory).all()
        total = len(rows)
        for i, vm in enumerate(rows):
            vm.embedding = embed(vm.content)
            if (i + 1) % 50 == 0:
                logger.info("Re-embedded %d / %d memories", i + 1, total)

    logger.info("Embedding migration complete: %d memories re-embedded to %d-dim", total, EMBEDDING_DIM)
