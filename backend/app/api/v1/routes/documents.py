"""
documents.py — Document browsing routes.

GET /documents      → list documents (filterable by source_type, process)
GET /documents/{id} → full document text
"""

from fastapi import APIRouter, Query
from app.db.connection import get_db

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("")
def list_documents(
    source_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    conn = get_db()
    filters, params = [], []
    if source_type:
        filters.append("source_type = ?")
        params.append(source_type)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    rows = conn.execute(
        f"SELECT id, source_id, source_type, author_handle, channel_or_space, timestamp, title, url "
        f"FROM documents {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{doc_id}")
def get_document(doc_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document not found")
    return dict(row)
