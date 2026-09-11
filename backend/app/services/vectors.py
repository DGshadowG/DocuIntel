"""Vector serialization and cosine-similarity search.

Embeddings are stored as float32 bytes in the `embeddings` table and searched
in-process with NumPy. For this system's corpus size (tens to low thousands of
chunks) a brute-force cosine scan is fast (<10 ms) and has zero infrastructure
cost. The PostgreSQL + pgvector migration path is documented in ADR-003.
"""
from typing import List, Optional, Sequence, Tuple

import numpy as np
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, Embedding


def to_bytes(vector: Sequence[float]) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_bytes(raw: bytes) -> np.ndarray:
    return np.frombuffer(raw, dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def semantic_search(
    db: Session,
    query_vector: Sequence[float],
    repository_ids: List[int],
    top_k: int = 6,
    document_ids: Optional[List[int]] = None,
) -> List[Tuple[DocumentChunk, Document, float]]:
    """Return top_k (chunk, document, similarity) within the given repositories."""
    if not repository_ids:
        return []
    query = (
        db.query(Embedding, DocumentChunk, Document)
        .join(DocumentChunk, Embedding.chunk_id == DocumentChunk.id)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.repository_id.in_(repository_ids))
        .filter(Document.status == "completed")
    )
    if document_ids:
        query = query.filter(Document.id.in_(document_ids))
    rows = query.all()
    if not rows:
        return []
    q = np.asarray(query_vector, dtype=np.float32)
    scored = []
    for embedding, chunk, document in rows:
        vec = from_bytes(embedding.vector)
        if vec.shape != q.shape:
            continue  # embeddings from a different model/dim are not comparable
        scored.append((chunk, document, cosine_similarity(q, vec)))
    scored.sort(key=lambda item: item[2], reverse=True)
    return scored[:top_k]
